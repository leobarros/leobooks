"""Modelos de dados do LeoBooks (SQLAlchemy + SQLite).

Toda entidade de domínio pertence a um usuário. O isolamento é garantido nas
consultas (sempre filtradas por ``user_id``) e por chaves estrangeiras com
``ON DELETE CASCADE``. IDs são UUID v4 em texto, como no esquema SQL.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Iterable

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

from utils.text import strip_accents

db = SQLAlchemy()

BOOK_STATUSES = {
    "WANT_TO_READ": {"label": "Quero ler", "icon": "bi-bookmark", "tone": "muted"},
    "READING": {"label": "Lendo", "icon": "bi-book-half", "tone": "forest"},
    "READ": {"label": "Lido", "icon": "bi-check2-circle", "tone": "sage"},
    "ABANDONED": {"label": "Abandonado", "icon": "bi-slash-circle", "tone": "clay"},
}

BOOK_MEDIA = {
    "PHYSICAL": {
        "label": "Livro físico",
        "short": "Físico",
        "icon": "bi-book",
        "description": "Acompanhe pela página impressa.",
    },
    "DIGITAL": {
        "label": "Livro digital",
        "short": "Digital",
        "icon": "bi-tablet",
        "description": "Acompanhe pelo percentual exibido no aparelho.",
    },
}

NOTE_TYPES = {
    "QUOTE": {
        "label": "Citação",
        "plural": "Citações",
        "icon": "bi-quote",
        "tone": "ochre",
        "hint": "Um trecho exato, com página e capítulo.",
    },
    "SUMMARY": {
        "label": "Resumo",
        "plural": "Resumos",
        "icon": "bi-journal-text",
        "tone": "forest",
        "hint": "A ideia do capítulo com as suas palavras.",
    },
    "INSIGHT": {
        "label": "Insight",
        "plural": "Insights",
        "icon": "bi-lightbulb",
        "tone": "clay",
        "hint": "Uma conexão, pergunta ou pensamento solto.",
    },
}

TAG_COLORS = [
    "#1F4A3D",  # floresta
    "#B2573B",  # terracota
    "#A97A22",  # ocre
    "#5D6F52",  # sálvia
    "#6D4257",  # ameixa
    "#2E4A5E",  # azul-tinta
    "#8A5A2B",  # caramelo
    "#7A4A44",  # barro
]


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# SQLite não ativa chaves estrangeiras por padrão. Sem isso, os ON DELETE
# CASCADE do esquema seriam apenas decorativos.
@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):  # noqa: ANN001
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        # Busca sem acentos, disponível como unaccent(coluna) no SQLite.
        dbapi_connection.create_function(
            "unaccent", 1, strip_accents, deterministic=True
        )
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
        except sqlite3.DatabaseError:  # bases em memória ou FS sem suporte
            pass
        cursor.close()


note_tags = db.Table(
    "note_tags",
    db.Column(
        "note_id",
        db.String(36),
        db.ForeignKey("notes.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "tag_id",
        db.String(36),
        db.ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Index("idx_note_tags_tag_id", "tag_id"),
)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    theme = db.Column(db.String(10), nullable=False, default="light")
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    onboarding_completed = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    books = db.relationship(
        "Book",
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="select",
    )
    notes = db.relationship(
        "Note",
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="select",
    )
    tags = db.relationship(
        "Tag",
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="select",
    )

    @property
    def note_count(self) -> int:
        return Note.query.filter_by(user_id=self.id).count()

    @property
    def first_name(self) -> str:
        return (self.name or "").strip().split(" ")[0] or "leitor"

    @property
    def initials(self) -> str:
        parts = [p for p in (self.name or "").strip().split(" ") if p]
        if not parts:
            return "LB"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.email}>"


class Book(db.Model):
    __tablename__ = "books"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    user_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(255), nullable=False)
    authors = db.Column(db.Text, nullable=False)
    publisher = db.Column(db.String(150))
    isbn = db.Column(db.String(20))
    total_pages = db.Column(db.Integer, nullable=False, default=0)
    current_page = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default="READING")
    media_type = db.Column(db.String(20), nullable=False, default="PHYSICAL")
    percent_complete = db.Column(db.Float, nullable=False, default=0.0)
    cover_url = db.Column(db.Text)
    cover_filename = db.Column(db.String(255))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    owner = db.relationship("User", back_populates="books")
    notes = db.relationship(
        "Note",
        back_populates="book",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="select",
        order_by="desc(Note.created_at)",
    )

    __table_args__ = (
        db.Index("idx_books_status", "status"),
        db.CheckConstraint(
            "status IN ('WANT_TO_READ', 'READING', 'READ', 'ABANDONED')",
            name="ck_books_status",
        ),
        db.CheckConstraint(
            "media_type IN ('PHYSICAL', 'DIGITAL')",
            name="ck_books_media_type",
        ),
    )

    # --- Apresentação ------------------------------------------------------
    @property
    def status_meta(self) -> dict:
        return BOOK_STATUSES.get(self.status, BOOK_STATUSES["READING"])

    @property
    def status_label(self) -> str:
        return self.status_meta["label"]

    @property
    def status_icon(self) -> str:
        return self.status_meta["icon"]

    @property
    def is_digital(self) -> bool:
        return (self.media_type or "PHYSICAL") == "DIGITAL"

    @property
    def media_meta(self) -> dict:
        return BOOK_MEDIA.get(self.media_type or "PHYSICAL", BOOK_MEDIA["PHYSICAL"])

    @property
    def media_label(self) -> str:
        return self.media_meta["label"]

    @property
    def media_short(self) -> str:
        return self.media_meta["short"]

    @property
    def media_icon(self) -> str:
        return self.media_meta["icon"]

    @property
    def progress_percent(self) -> int:
        if self.is_digital:
            return max(0, min(100, round(float(self.percent_complete or 0))))
        if not self.total_pages or self.total_pages <= 0:
            return 0
        return max(0, min(100, round((self.current_page or 0) * 100 / self.total_pages)))

    @property
    def pages_remaining(self) -> int:
        return max(0, (self.total_pages or 0) - (self.current_page or 0))

    @property
    def has_custom_cover(self) -> bool:
        return bool(self.cover_filename or self.cover_url)

    @property
    def note_count(self) -> int:
        # COUNT não materializa o conteúdo das notas (importante em bibliotecas grandes).
        return Note.query.filter_by(book_id=self.id).count()

    @property
    def last_note(self):
        return (
            Note.query.filter_by(book_id=self.id)
            .order_by(Note.created_at.desc())
            .first()
        )

    @property
    def quote_count(self) -> int:
        return sum(1 for note in self.notes if note.type == "QUOTE")

    @property
    def summary_count(self) -> int:
        return sum(1 for note in self.notes if note.type == "SUMMARY")

    @property
    def insight_count(self) -> int:
        return sum(1 for note in self.notes if note.type == "INSIGHT")

    def tags(self) -> list["Tag"]:
        seen: dict[str, Tag] = {}
        for note in self.notes:
            for tag in note.tags:
                seen[tag.id] = tag
        return sorted(seen.values(), key=lambda t: t.name.lower())

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Book {self.title!r}>"


class Note(db.Model):
    __tablename__ = "notes"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    user_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    book_id = db.Column(
        db.String(36),
        db.ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type = db.Column(db.String(20), nullable=False, default="QUOTE")
    content = db.Column(db.Text, nullable=False)
    page_number = db.Column(db.Integer)
    chapter = db.Column(db.String(100))
    image_filename = db.Column(db.String(255))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    owner = db.relationship("User", back_populates="notes")
    book = db.relationship("Book", back_populates="notes")
    tags = db.relationship(
        "Tag",
        secondary=note_tags,
        back_populates="notes",
        lazy="selectin",
        order_by="Tag.name",
    )

    __table_args__ = (
        db.Index("idx_notes_type", "type"),
        db.Index("idx_notes_created_at", "created_at"),
        db.CheckConstraint(
            "type IN ('QUOTE', 'SUMMARY', 'INSIGHT')", name="ck_notes_type"
        ),
    )

    # --- Apresentação ------------------------------------------------------
    @property
    def type_meta(self) -> dict:
        return NOTE_TYPES.get(self.type, NOTE_TYPES["QUOTE"])

    @property
    def type_label(self) -> str:
        return self.type_meta["label"]

    @property
    def type_icon(self) -> str:
        return self.type_meta["icon"]

    @property
    def type_tone(self) -> str:
        return self.type_meta["tone"]

    @property
    def html(self):
        """Markdown convertido e sanitizado (seguro para o template)."""
        from utils.markdown_helper import render_markdown

        return render_markdown(self.content or "")

    @property
    def plain_text(self) -> str:
        from utils.markdown_helper import plain_text as to_plain

        return to_plain(self.content or "")

    @property
    def excerpt(self) -> str:
        text = self.plain_text
        return text if len(text) <= 220 else text[:217].rstrip() + "…"

    @property
    def location_label(self) -> str:
        parts = []
        if self.chapter:
            parts.append(f"Cap. {self.chapter}")
        if self.page_number is not None:
            parts.append(f"pág. {self.page_number}")
        return " · ".join(parts)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "book_id": self.book_id,
            "type": self.type,
            "content": self.content,
            "chapter": self.chapter,
            "page_number": self.page_number,
            "tags": [tag.name for tag in self.tags],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Note {self.type} {self.id[:8]}>"


class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.String(36), primary_key=True, default=new_id)
    user_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(50), nullable=False)
    color_hex = db.Column(db.String(7), nullable=False, default="#5D6F52")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    owner = db.relationship("User", back_populates="tags")
    notes = db.relationship(
        "Note",
        secondary=note_tags,
        back_populates="tags",
        lazy="select",
        order_by="desc(Note.created_at)",
    )

    __table_args__ = (
        db.UniqueConstraint("user_id", "name", name="uq_tags_user_name"),
        db.Index("idx_tags_name", "name"),
    )

    @property
    def count(self) -> int:
        return Note.query.filter_by(user_id=self.user_id).filter(
            Note.tags.any(Tag.id == self.id)
        ).count()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "color_hex": self.color_hex,
            "count": self.count,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Tag {self.name!r}>"


def seed_reference_data(user: User) -> Iterable[Tag]:  # pragma: no cover - conveniência
    return user.tags
