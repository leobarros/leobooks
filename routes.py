"""Rotas WSGI do LeoBooks, organizadas em blueprints.

Toda consulta de livro/nota/tag é filtrada pelo ``user_id`` da sessão — o
isolamento entre contas é uma regra de segurança, não apenas de UX.
"""

from __future__ import annotations

import io
import json
import shutil
import sqlite3
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)
from sqlalchemy import case, func, or_
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from forms import (
    BookForm,
    DeleteAccountForm,
    LoginForm,
    NewUserForm,
    NoteForm,
    PasswordForm,
    ProfileForm,
    RegisterForm,
    RestoreForm,
)
from helpers import (
    admin_required,
    cleanup_orphan_tags,
    create_sample_book,
    current_user,
    greeting_for_now,
    login_required,
    parse_tag_names,
    reading_streak_dates,
    redirect_back,
    resolve_tags,
    safe_next_url,
    week_activity,
    weekday_long,
    week_activity_dates,
)
from models import (
    BOOK_MEDIA,
    BOOK_STATUSES,
    NOTE_TYPES,
    Book,
    Note,
    Tag,
    User,
    db,
    utcnow,
)
from utils.audit import audit
from utils.backup import (
    BackupError,
    build_full_backup,
    extract_and_validate,
    validate_sqlite,
)
from utils.text import strip_accents
from utils.book_lookup import (
    CoverLookupError,
    save_cover_from_url,
    search_cover_candidates,
    verify_cover_token,
)
from utils.cover_art import cover_svg
from utils.media import MediaError, remove_image, save_image
from utils.ocr import extract_text, ocr_available

auth_bp = Blueprint("auth", __name__)
main_bp = Blueprint("main", __name__)
books_bp = Blueprint("books", __name__)
notes_bp = Blueprint("notes", __name__)
settings_bp = Blueprint("settings", __name__)

CURATED_QUOTE = {
    "text": "Sua mente é para ter ideias, não para guardá-las.",
    "author": "David Allen",
    "source": "A Arte de Fazer Acontecer",
    "tags": ["método", "atenção"],
}


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------
def _owned_book(book_id: str) -> Book:
    book = Book.query.filter_by(id=book_id, user_id=current_user().id).first()
    if book is None:
        abort(404)
    return book


def _owned_note(note_id: str) -> Note:
    note = Note.query.filter_by(id=note_id, user_id=current_user().id).first()
    if note is None:
        abort(404)
    return note


def _first_error(form) -> str:
    for errors in form.errors.values():
        if errors:
            return errors[0]
    return "Confira os dados do formulário."


def _note_form() -> NoteForm:
    """Formulário de nota com os livros do usuário como opções."""
    form = NoteForm()
    books = (
        Book.query.filter_by(user_id=current_user().id)
        .order_by(Book.updated_at.desc())
        .all()
    )
    form.book_id.choices = [(book.id, f"{book.title} — {book.authors}") for book in books]
    return form


def _apply_note_form(note: Note, form: NoteForm) -> None:
    note.type = form.type.data if form.type.data in NOTE_TYPES else "QUOTE"
    note.content = (form.content.data or "").strip()
    note.chapter = (form.chapter.data or "").strip() or None
    note.page_number = form.page_number.data
    note.tags = resolve_tags(current_user(), parse_tag_names(form.tags.data))
    note.updated_at = utcnow()


def _save_note_photo(form: NoteForm, note: Note) -> None:
    try:
        filename = save_image(
            form.photo.data,
            Path(current_app.config["UPLOAD_FOLDER"]),
            max_size=(1700, 1700),
        )
    except MediaError as exc:
        raise ValueError(str(exc)) from exc
    if filename:
        remove_image(Path(current_app.config["UPLOAD_FOLDER"]), note.image_filename)
        note.image_filename = filename


def _cover_from_candidate() -> str | None:
    """Baixa e salva a capa escolhida no seletor de capas públicas."""
    token = (request.form.get("cover_candidate") or "").strip()
    if not token:
        return None

    url = verify_cover_token(token)
    if not url:
        audit(
            "cover.download_failed",
            outcome="failure",
            severity="warning",
            reason="token_expired",
        )
        flash("A capa escolhida expirou. Busque novamente antes de salvar.", "warning")
        return None

    try:
        filename = save_cover_from_url(url, Path(current_app.config["COVER_FOLDER"]))
        audit(
            "cover.download",
            host=urlparse(url).hostname,
            filename=filename,
        )
        return filename
    except CoverLookupError as exc:
        audit(
            "cover.download_failed",
            outcome="failure",
            severity="warning",
            reason=exc.code,
            host=urlparse(url).hostname,
        )
        flash(exc.message, "warning")
        return None


def _sqlite_path() -> Path:
    url = db.engine.url
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        abort(400, description="Backup disponível apenas para banco SQLite em arquivo.")
    return Path(url.database)


def _daily_quote(user: User) -> dict:
    """Escolhe a citação do dia sem carregar o caderno inteiro na memória."""
    quote_query = Note.query.filter_by(user_id=user.id, type="QUOTE")
    total = quote_query.count()
    pool_query = quote_query
    if not total:
        pool_query = Note.query.filter_by(user_id=user.id)
        total = pool_query.count()

    if total:
        index = date.today().toordinal() % total
        chosen = (
            pool_query.order_by(Note.created_at.asc())
            .offset(index)
            .limit(1)
            .first()
        )
        if chosen is not None:
            source = chosen.book
            return {
                "note": chosen,
                "share_text": chosen.plain_text,
                "share_source": f"{source.authors} · {source.title}" if source else "",
                "share_tags": [tag.name for tag in chosen.tags],
                "location": chosen.location_label,
                "url": url_for("books.detail", book_id=source.id) if source else None,
                "is_curated": False,
            }
    return {
        "note": None,
        "share_text": CURATED_QUOTE["text"],
        "share_source": f"{CURATED_QUOTE['author']} · {CURATED_QUOTE['source']}",
        "share_tags": CURATED_QUOTE["tags"],
        "location": "sugestão do LeoBooks",
        "url": None,
        "is_curated": True,
    }


def _reading_stats(user: User, note_dates=None) -> dict:
    """Contagens via SQL, sem materializar livros/notas/tags completos."""
    book_stats = (
        db.session.query(
            func.count(Book.id),
            func.coalesce(
                func.sum(case((Book.status == "READING", 1), else_=0)), 0
            ),
            func.coalesce(func.sum(case((Book.status == "READ", 1), else_=0)), 0),
            func.coalesce(func.sum(Book.current_page), 0),
        )
        .filter(Book.user_id == user.id)
        .one()
    )
    note_stats = (
        db.session.query(
            func.count(Note.id),
            func.coalesce(func.sum(case((Note.type == "QUOTE", 1), else_=0)), 0),
            func.coalesce(func.sum(case((Note.type == "SUMMARY", 1), else_=0)), 0),
            func.coalesce(func.sum(case((Note.type == "INSIGHT", 1), else_=0)), 0),
        )
        .filter(Note.user_id == user.id)
        .one()
    )
    return {
        "books": int(book_stats[0] or 0),
        "reading": int(book_stats[1] or 0),
        "read": int(book_stats[2] or 0),
        "notes": int(note_stats[0] or 0),
        "quotes": int(note_stats[1] or 0),
        "summaries": int(note_stats[2] or 0),
        "insights": int(note_stats[3] or 0),
        "pages": int(book_stats[3] or 0),
        "tags": Tag.query.filter_by(user_id=user.id).count(),
        "streak": reading_streak_dates(note_dates or []),
    }


def _start_session(user: User, remember: bool = True) -> None:
    session.clear()
    session["user_id"] = user.id
    session.permanent = bool(remember)
    # Deixa o contexto atual consistente para logs/redirects desta requisição.
    g.current_user = user


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------
_DUMMY_HASH = generate_password_hash("senha-inexistente")


def _looks_like_user(email: str) -> User | None:
    return User.query.filter(func.lower(User.email) == email.lower()).first()


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        email = (form.email.data or "").strip()
        password = form.password.data or ""
        user = _looks_like_user(email)
        valid = check_password_hash(user.password_hash if user else _DUMMY_HASH, password)
        if user and valid:
            _start_session(user, remember=bool(form.remember.data))
            audit("auth.login", user_id=user.id, user_email=user.email)
            flash(f"Que bom te ver, {user.first_name}.", "success")
            target = safe_next_url(request.args.get("next")) or url_for("main.dashboard")
            return redirect(target)
        audit(
            "auth.login_failed",
            outcome="failure",
            severity="warning",
            reason="invalid_credentials",
            attempted_email=email,
        )
        flash("E-mail ou senha incorretos.", "danger")

    return render_template(
        "auth/login.html", form=form, next_url=request.args.get("next", "")
    )


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user():
        return redirect(url_for("main.dashboard"))

    form = RegisterForm()
    if form.validate_on_submit():
        email = (form.email.data or "").strip().lower()
        if _looks_like_user(email):
            audit(
                "auth.register_failed",
                outcome="failure",
                severity="warning",
                reason="email_in_use",
                attempted_email=email,
            )
            flash("Este e-mail já está em uso. Tente entrar.", "warning")
            return render_template("auth/register.html", form=form)

        is_first_user = User.query.count() == 0
        user = User(
            name=(form.name.data or "").strip(),
            email=email,
            password_hash=generate_password_hash(form.password.data),
            theme=Config.DEFAULT_THEME,
            is_admin=is_first_user,
            onboarding_completed=False,
        )
        db.session.add(user)
        db.session.flush()

        sample_book = None
        if current_app.config.get("SAMPLE_BOOK_ENABLED", True):
            sample_book = create_sample_book(user)
        db.session.commit()

        _start_session(user, remember=True)
        audit(
            "auth.register",
            user_id=user.id,
            user_email=user.email,
            is_admin=bool(user.is_admin),
            sample_book=bool(sample_book),
        )
        if sample_book is not None:
            audit(
                "book.create",
                book_id=sample_book.id,
                title=sample_book.title,
                status=sample_book.status,
                total_pages=sample_book.total_pages,
                sample=True,
            )
        if sample_book is not None:
            flash(
                "Sua conta está pronta. Deixamos um livro de exemplo para você começar.",
                "success",
            )
        else:
            flash("Sua conta está pronta. Bem-vindo ao seu caderno de leitura.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    user = current_user()
    if user is not None:
        audit("auth.logout", user_id=user.id, user_email=user.email)
    session.clear()
    flash("Sessão encerrada. Até a próxima leitura.", "info")
    return redirect(url_for("auth.login"))


# ---------------------------------------------------------------------------
# Início / biblioteca / busca / tags / revisão
# ---------------------------------------------------------------------------
@main_bp.route("/")
@login_required
def dashboard():
    user = current_user()
    notes = (
        Note.query.filter_by(user_id=user.id)
        .order_by(Note.created_at.desc())
        .limit(4)
        .all()
    )
    books = (
        Book.query.filter_by(user_id=user.id)
        .order_by(Book.updated_at.desc())
        .all()
    )
    reading = [book for book in books if book.status == "READING"]
    # Só timestamps: suficiente para streak e atividade, sem carregar conteúdo.
    note_dates = [
        row[0]
        for row in db.session.query(Note.created_at)
        .filter(Note.user_id == user.id)
        .all()
    ]
    stats = _reading_stats(user, note_dates)

    top_tags = sorted(user.tags, key=lambda tag: (-tag.count, tag.name))[:6]
    daily_quote = _daily_quote(user)

    return render_template(
        "dashboard.html",
        notes=notes,
        books=books,
        reading=reading[:4],
        stats=stats,
        top_tags=top_tags,
        daily_quote=daily_quote,
        greeting=greeting_for_now(),
        weekday=weekday_long(),
        activity=week_activity_dates(note_dates),
    )


@main_bp.route("/library")
@login_required
def library():
    user = current_user()
    status_filter = (request.args.get("status") or "").strip().upper()
    query_text = (request.args.get("q") or "").strip()[:120]
    sort = request.args.get("sort", "recent")

    query = Book.query.filter_by(user_id=user.id)
    if status_filter in BOOK_STATUSES:
        query = query.filter(Book.status == status_filter)
    if query_text:
        like = f"%{strip_accents(query_text)}%"
        query = query.filter(
            or_(
                func.unaccent(Book.title).ilike(like),
                func.unaccent(Book.authors).ilike(like),
                func.unaccent(Book.publisher).ilike(like),
            )
        )

    if sort == "title":
        query = query.order_by(Book.title.asc())
    elif sort == "progress":
        query = query.order_by(
            (Book.current_page * 1.0 / func.nullif(Book.total_pages, 0)).desc()
        )
    else:
        status_rank = case(
            (Book.status == "READING", 0),
            (Book.status == "WANT_TO_READ", 1),
            (Book.status == "READ", 2),
            else_=3,
        )
        query = query.order_by(status_rank, Book.updated_at.desc())

    books = query.all()
    all_books = user.books
    counts = {"ALL": len(all_books)}
    for key in BOOK_STATUSES:
        counts[key] = sum(1 for book in all_books if book.status == key)

    return render_template(
        "library.html",
        books=books,
        counts=counts,
        status_filter=status_filter,
        query_text=query_text,
        sort=sort,
    )


@main_bp.route("/tags")
@login_required
def tags():
    user = current_user()
    tags = sorted(user.tags, key=lambda tag: (-tag.count, tag.name))
    recent_notes = (
        Note.query.filter_by(user_id=user.id).order_by(Note.created_at.desc()).limit(8).all()
    )
    return render_template("tags.html", tags=tags, selected_tag=None, notes=recent_notes)


@main_bp.route("/tags/<tag_id>")
@login_required
def tag_detail(tag_id: str):
    tag = Tag.query.filter_by(id=tag_id, user_id=current_user().id).first_or_404()
    return render_template(
        "tags.html",
        tags=sorted(current_user().tags, key=lambda item: (-item.count, item.name)),
        selected_tag=tag,
        notes=tag.notes,
    )


@main_bp.route("/review")
@login_required
def review():
    user = current_user()
    quote_query = Note.query.filter_by(user_id=user.id, type="QUOTE")
    total = quote_query.count()
    pool_query = quote_query
    if not total:
        pool_query = Note.query.filter_by(user_id=user.id)
        total = pool_query.count()
    if not total:
        return render_template("review.html", note=None, total=0, index=0, next_seed=1)

    seed = request.args.get("seed", type=int)
    index = (date.today().toordinal() if seed is None else max(0, seed)) % total
    note = (
        pool_query.order_by(Note.created_at.desc())
        .offset(index)
        .limit(1)
        .first()
    )
    return render_template(
        "review.html",
        note=note,
        total=total,
        index=index,
        next_seed=index + 1,
    )


@main_bp.route("/search")
@login_required
def search():
    user = current_user()
    query_text = (request.args.get("q") or "").strip()[:120]
    books: list[Book] = []
    notes: list[Note] = []
    tags: list[Tag] = []

    if query_text:
        like = f"%{strip_accents(query_text)}%"
        books = (
            Book.query.filter(
                Book.user_id == user.id,
                or_(
                    func.unaccent(Book.title).ilike(like),
                    func.unaccent(Book.authors).ilike(like),
                    func.unaccent(Book.publisher).ilike(like),
                    Book.isbn.ilike(like),
                ),
            )
            .order_by(Book.updated_at.desc())
            .limit(24)
            .all()
        )
        notes = (
            Note.query.filter(
                Note.user_id == user.id,
                or_(
                    func.unaccent(Note.content).ilike(like),
                    func.unaccent(Note.chapter).ilike(like),
                ),
            )
            .order_by(Note.created_at.desc())
            .limit(60)
            .all()
        )
        tags = (
            Tag.query.filter(
                Tag.user_id == user.id,
                func.unaccent(Tag.name).ilike(like),
            )
            .order_by(Tag.name.asc())
            .limit(24)
            .all()
        )
        if tags:
            tag_ids = [tag.id for tag in tags]
            tag_notes = (
                Note.query.filter(
                    Note.user_id == user.id,
                    Note.tags.any(Tag.id.in_(tag_ids)),
                )
                .order_by(Note.created_at.desc())
                .limit(30)
                .all()
            )
            seen = {note.id for note in notes}
            notes.extend(note for note in tag_notes if note.id not in seen)

    total = len(books) + len(notes) + len(tags)
    return render_template(
        "search.html",
        query_text=query_text,
        books=books,
        notes=notes,
        tags=tags,
        total=total,
    )


# ---------------------------------------------------------------------------
# Livros
# ---------------------------------------------------------------------------
@books_bp.route("/books/new", methods=["GET", "POST"])
@login_required
def new():
    user = current_user()
    if not user.books and request.method == "GET":
        flash("Comece cadastrando o livro que está lendo.", "info")

    form = BookForm()
    if form.validate_on_submit():
        media_type = (
            form.media_type.data
            if form.media_type.data in BOOK_MEDIA
            else "PHYSICAL"
        )
        total_pages = form.total_pages.data or 0
        current_page = form.current_page.data or 0
        percent_complete = 0.0
        if media_type == "DIGITAL":
            percent_complete = max(
                0.0, min(100.0, float(form.current_percent.data or 0))
            )
            current_page = (
                round(total_pages * percent_complete / 100) if total_pages else 0
            )
        else:
            current_page = min(max(current_page, 0), total_pages or current_page)

        book = Book(
            user_id=user.id,
            title=(form.title.data or "").strip(),
            authors=(form.authors.data or "").strip(),
            publisher=(form.publisher.data or "").strip() or None,
            isbn=form.isbn.data,
            total_pages=total_pages,
            current_page=current_page,
            media_type=media_type,
            percent_complete=percent_complete,
            status=form.status.data,
            cover_url=(form.cover_url.data or "").strip() or None,
        )
        try:
            book.cover_filename = save_image(
                form.cover.data,
                Path(current_app.config["COVER_FOLDER"]),
                max_size=(1200, 1800),
            )
        except MediaError as exc:
            form.cover.errors.append(str(exc))
            return render_template("book_form.html", form=form, book=None), 400

        if not book.cover_filename:
            book.cover_filename = _cover_from_candidate()

        if book.is_digital:
            if percent_complete >= 100:
                book.status = "READ"
        elif book.total_pages and book.current_page >= book.total_pages:
            book.status = "READ"
        db.session.add(book)
        db.session.commit()
        audit(
            "book.create",
            book_id=book.id,
            title=book.title,
            media_type=book.media_type,
            status=book.status,
            total_pages=book.total_pages,
            current_page=book.current_page,
            percent_complete=book.percent_complete if book.is_digital else None,
            has_cover=bool(book.cover_filename or book.cover_url),
        )
        flash(f"“{book.title}” entrou para a sua estante.", "success")
        return redirect(url_for("books.detail", book_id=book.id))

    return render_template("book_form.html", form=form, book=None)


@books_bp.route("/books/<book_id>/edit", methods=["GET", "POST"])
@login_required
def edit(book_id: str):
    book = _owned_book(book_id)
    form = BookForm(obj=book)
    if request.method == "GET":
        form.media_type.data = book.media_type or "PHYSICAL"
        form.current_page.data = book.current_page
        form.current_percent.data = (
            round(book.percent_complete or 0) if book.is_digital else 0
        )
        form.status.data = book.status

    if form.validate_on_submit():
        old_media = book.media_type or "PHYSICAL"
        old_percent = (
            float(book.percent_complete or 0)
            if old_media == "DIGITAL"
            else float(book.progress_percent)
        )
        media_type = (
            form.media_type.data
            if form.media_type.data in BOOK_MEDIA
            else "PHYSICAL"
        )
        total_pages = form.total_pages.data or 0

        if media_type == "DIGITAL":
            if old_media == "DIGITAL":
                percent_complete = max(
                    0.0, min(100.0, float(form.current_percent.data or 0))
                )
            else:
                percent_complete = max(0.0, min(100.0, old_percent))
            current_page = (
                round(total_pages * percent_complete / 100) if total_pages else 0
            )
        else:
            if old_media == "DIGITAL":
                current_page = (
                    round(total_pages * old_percent / 100) if total_pages else 0
                )
            else:
                current_page = form.current_page.data or 0
            current_page = min(max(current_page, 0), total_pages or current_page)
            percent_complete = 0.0

        book.title = (form.title.data or "").strip()
        book.authors = (form.authors.data or "").strip()
        book.publisher = (form.publisher.data or "").strip() or None
        book.isbn = form.isbn.data
        book.total_pages = total_pages
        book.current_page = current_page
        book.media_type = media_type
        book.percent_complete = percent_complete
        book.status = form.status.data
        book.cover_url = (form.cover_url.data or "").strip() or None

        try:
            new_cover = save_image(
                form.cover.data,
                Path(current_app.config["COVER_FOLDER"]),
                max_size=(1200, 1800),
            )
        except MediaError as exc:
            form.cover.errors.append(str(exc))
            return render_template("book_form.html", form=form, book=book), 400

        candidate_cover = None
        if not new_cover:
            candidate_cover = _cover_from_candidate()

        if new_cover or candidate_cover:
            remove_image(Path(current_app.config["COVER_FOLDER"]), book.cover_filename)
            book.cover_filename = new_cover or candidate_cover
        elif form.remove_cover.data:
            remove_image(Path(current_app.config["COVER_FOLDER"]), book.cover_filename)
            book.cover_filename = None
            book.cover_url = None

        if book.is_digital:
            if book.percent_complete >= 100:
                book.status = "READ"
        elif book.total_pages and book.current_page >= book.total_pages:
            book.status = "READ"
        book.updated_at = utcnow()
        db.session.commit()
        audit(
            "book.update",
            book_id=book.id,
            title=book.title,
            media_type=book.media_type,
            status=book.status,
            total_pages=book.total_pages,
            current_page=book.current_page,
            percent_complete=book.percent_complete if book.is_digital else None,
            has_cover=bool(book.cover_filename or book.cover_url),
        )
        flash("Livro atualizado.", "success")
        return redirect(url_for("books.detail", book_id=book.id))

    return render_template("book_form.html", form=form, book=book)


@books_bp.route("/books/cover-lookup", methods=["POST"])
@login_required
def cover_lookup():
    """Consulta Open Library/Google Books e devolve capas candidatas assinadas."""
    if not current_app.config.get("COVER_LOOKUP_ENABLED", True):
        audit(
            "cover.lookup_failed",
            outcome="failure",
            severity="warning",
            reason="disabled",
        )
        return (
            jsonify(
                ok=False,
                message="A busca de capas está desativada neste servidor.",
            ),
            503,
        )

    isbn = (request.form.get("isbn") or "").strip()[:25]
    title = (request.form.get("title") or "").strip()[:200]
    authors = (request.form.get("authors") or "").strip()[:200]

    if not isbn and not title:
        audit(
            "cover.lookup_failed",
            outcome="failure",
            severity="warning",
            reason="missing_query",
        )
        return (
            jsonify(
                ok=False,
                message="Informe o ISBN ou o título do livro para buscar capas.",
            ),
            400,
        )

    try:
        candidates = search_cover_candidates(isbn=isbn, title=title, authors=authors)
    except CoverLookupError as exc:
        current_app.logger.warning("Busca de capas falhou: %s", exc)
        audit(
            "cover.lookup_failed",
            outcome="failure",
            severity="warning",
            reason=exc.code,
            isbn=isbn or None,
        )
        return jsonify(ok=False, code=exc.code, message=exc.message), 502

    if not candidates:
        audit(
            "cover.lookup",
            isbn=isbn or None,
            query_type="both" if isbn and title else ("isbn" if isbn else "title"),
            result_count=0,
        )
        return jsonify(
            ok=True,
            candidates=[],
            message="Nenhuma capa encontrada. Tente outro título, autor ou ISBN.",
        )

    audit(
        "cover.lookup",
        isbn=isbn or None,
        query_type="both" if isbn and title else ("isbn" if isbn else "title"),
        result_count=len(candidates),
        sources=sorted({candidate.get("source") for candidate in candidates}),
    )
    return jsonify(
        ok=True,
        candidates=candidates,
        message=f"{len(candidates)} capa{'s' if len(candidates) != 1 else ''} encontrada{'s' if len(candidates) != 1 else ''}.",
    )


@books_bp.route("/books/<book_id>")
@login_required
def detail(book_id: str):
    book = _owned_book(book_id)
    type_filter = (request.args.get("type") or "ALL").upper()
    if type_filter not in NOTE_TYPES:
        type_filter = "ALL"

    notes = book.notes
    if type_filter != "ALL":
        notes = [note for note in notes if note.type == type_filter]

    counts = {
        "ALL": len(book.notes),
        "QUOTE": book.quote_count,
        "SUMMARY": book.summary_count,
        "INSIGHT": book.insight_count,
    }
    return render_template(
        "book_detail.html",
        book=book,
        notes=notes,
        type_filter=type_filter,
        counts=counts,
    )


@books_bp.route("/books/<book_id>/progress", methods=["POST"])
@login_required
def progress(book_id: str):
    book = _owned_book(book_id)
    mode = (request.form.get("progress_mode") or "").strip().lower()
    percent: float | None = None
    page: int | None = None

    if book.is_digital:
        percent = request.form.get("percent", type=float)
        if percent is None:
            # Compatibilidade com formulários antigos que enviavam página.
            legacy_page = request.form.get("current_page", type=int)
            if legacy_page is not None and book.total_pages:
                percent = legacy_page * 100 / book.total_pages
        if percent is None or percent < 0 or percent > 100:
            audit(
                "book.progress_failed",
                outcome="failure",
                severity="warning",
                reason="invalid_percent",
                book_id=book.id,
                mode="percent",
                media_type=book.media_type,
            )
            flash("Informe um percentual entre 0 e 100.", "danger")
            return redirect_back("books.detail", fallback_kwargs={"book_id": book.id})

        percent = max(0.0, min(100.0, percent))
        page = round((book.total_pages or 0) * percent / 100) if book.total_pages else 0
        book.percent_complete = percent
        book.current_page = page
        progress_label = f"{percent:g}% no livro digital"
        if book.total_pages:
            progress_label += f" (≈ página {page} de {book.total_pages})"
        completed = percent >= 100
        mode = "percent"
    else:
        page = request.form.get("current_page", type=int)
        if page is None:
            # Compatibilidade com formulários antigos que enviavam percentual.
            legacy_percent = request.form.get("percent", type=float)
            if legacy_percent is not None and book.total_pages:
                percent = max(0.0, min(100.0, legacy_percent))
                page = round(book.total_pages * percent / 100)
        if page is None or page < 0 or (book.total_pages and page > book.total_pages):
            audit(
                "book.progress_failed",
                outcome="failure",
                severity="warning",
                reason="invalid_page",
                book_id=book.id,
                mode="page",
                media_type=book.media_type,
            )
            flash("Página inválida para este livro.", "danger")
            return redirect_back("books.detail", fallback_kwargs={"book_id": book.id})

        book.current_page = page
        book.percent_complete = 0.0
        progress_label = f"página {page}"
        if book.total_pages:
            progress_label += f" de {book.total_pages}"
        completed = bool(book.total_pages and page >= book.total_pages)
        mode = "page"

    book.updated_at = utcnow()

    if completed:
        book.status = "READ"
        flash("Você concluiu o livro. Que tal registrar a última impressão?", "success")
    elif (book.is_digital and percent and percent > 0) or (
        not book.is_digital and page and page > 0
    ):
        if book.status == "WANT_TO_READ":
            book.status = "READING"
        flash(
            f"Progresso atualizado para {progress_label}. "
            "Bom ritmo de leitura.",
            "success",
        )
    else:
        flash(f"Progresso atualizado: {progress_label}.", "success")

    db.session.commit()
    audit(
        "book.progress",
        book_id=book.id,
        mode=mode,
        media_type=book.media_type,
        page=book.current_page,
        percent=percent if book.is_digital else None,
        status=book.status,
    )
    return redirect(url_for("books.detail", book_id=book.id))


@books_bp.route("/books/<book_id>/status", methods=["POST"])
@login_required
def status(book_id: str):
    book = _owned_book(book_id)
    new_status = (request.form.get("status") or "").upper()
    if new_status not in BOOK_STATUSES:
        audit(
            "book.status_failed",
            outcome="failure",
            severity="warning",
            reason="invalid_status",
            book_id=book.id,
        )
        flash("Status inválido.", "danger")
        return redirect(url_for("books.detail", book_id=book.id))

    previous_status = book.status
    book.status = new_status
    if new_status == "READ":
        if book.is_digital:
            book.percent_complete = 100.0
            book.current_page = book.total_pages or 0
        elif book.total_pages:
            book.current_page = book.total_pages
    book.updated_at = utcnow()
    db.session.commit()
    audit(
        "book.status",
        book_id=book.id,
        from_status=previous_status,
        to_status=book.status,
        media_type=book.media_type,
        current_page=book.current_page,
        percent=book.percent_complete if book.is_digital else None,
    )
    flash(f"Status alterado para “{book.status_label}”.", "success")
    return redirect(url_for("books.detail", book_id=book.id))


@books_bp.route("/books/<book_id>/delete", methods=["POST"])
@login_required
def delete(book_id: str):
    book = _owned_book(book_id)
    title = book.title
    note_count = len(book.notes)
    upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
    for note in book.notes:
        remove_image(upload_folder, note.image_filename)
    remove_image(Path(current_app.config["COVER_FOLDER"]), book.cover_filename)
    db.session.delete(book)
    db.session.commit()
    cleanup_orphan_tags(current_user().id)
    audit("book.delete", book_id=book_id, title=title, notes=note_count)
    flash(f"“{title}” e suas notas foram removidos.", "info")
    return redirect(url_for("main.library"))


@books_bp.route("/books/<book_id>/cover.svg")
@login_required
def cover(book_id: str):
    book = _owned_book(book_id)
    svg = cover_svg(book.title, book.authors, seed=book.id)
    response = Response(svg, mimetype="image/svg+xml")
    response.headers["Cache-Control"] = "private, max-age=86400"
    return response


@books_bp.route("/media/covers/<filename>")
@login_required
def cover_image(filename: str):
    safe_name = Path(filename).name
    book = Book.query.filter_by(
        user_id=current_user().id, cover_filename=safe_name
    ).first_or_404()
    return send_from_directory(
        current_app.config["COVER_FOLDER"], safe_name, max_age=3600
    )


# ---------------------------------------------------------------------------
# Notas
# ---------------------------------------------------------------------------
@notes_bp.route("/notes/new", methods=["POST"])
@login_required
def create():
    form = _note_form()
    if not form.validate_on_submit():
        flash(_first_error(form), "danger")
        return redirect_back("main.dashboard")

    book = Book.query.filter_by(
        id=form.book_id.data, user_id=current_user().id
    ).first()
    if book is None:
        abort(404)

    note = Note(
        user_id=current_user().id,
        book_id=book.id,
        type=form.type.data if form.type.data in NOTE_TYPES else "QUOTE",
        content=(form.content.data or "").strip(),
        chapter=(form.chapter.data or "").strip() or None,
        page_number=form.page_number.data,
    )
    note.tags = resolve_tags(current_user(), parse_tag_names(form.tags.data))
    try:
        _save_note_photo(form, note)
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect_back("books.detail", fallback_kwargs={"book_id": book.id})

    db.session.add(note)
    book.updated_at = utcnow()
    db.session.commit()
    audit(
        "note.create",
        note_id=note.id,
        book_id=book.id,
        note_type=note.type,
        page_number=note.page_number,
        tag_count=len(note.tags),
        has_photo=bool(note.image_filename),
    )
    flash("Nota guardada no seu caderno.", "success")
    return redirect_back("books.detail", fallback_kwargs={"book_id": book.id})


@notes_bp.route("/notes/<note_id>/edit", methods=["POST"])
@login_required
def edit(note_id: str):
    note = _owned_note(note_id)
    form = _note_form()
    if not form.validate_on_submit():
        flash(_first_error(form), "danger")
        return redirect_back("books.detail", fallback_kwargs={"book_id": note.book_id})

    book = Book.query.filter_by(
        id=form.book_id.data, user_id=current_user().id
    ).first()
    if book is None:
        abort(404)

    note.book_id = book.id
    _apply_note_form(note, form)
    try:
        _save_note_photo(form, note)
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect_back("books.detail", fallback_kwargs={"book_id": book.id})

    db.session.commit()
    cleanup_orphan_tags(current_user().id)
    audit(
        "note.update",
        note_id=note.id,
        book_id=book.id,
        note_type=note.type,
        page_number=note.page_number,
        tag_count=len(note.tags),
        has_photo=bool(note.image_filename),
    )
    flash("Nota atualizada.", "success")
    return redirect_back("books.detail", fallback_kwargs={"book_id": book.id})


@notes_bp.route("/notes/<note_id>/delete", methods=["POST"])
@login_required
def delete(note_id: str):
    note = _owned_note(note_id)
    book_id = note.book_id
    note_type = note.type
    remove_image(Path(current_app.config["UPLOAD_FOLDER"]), note.image_filename)
    db.session.delete(note)
    db.session.commit()
    cleanup_orphan_tags(current_user().id)
    audit("note.delete", note_id=note_id, book_id=book_id, note_type=note_type)
    flash("Nota removida.", "info")
    return redirect_back("books.detail", fallback_kwargs={"book_id": book_id})


@notes_bp.route("/notes/ocr", methods=["POST"])
@login_required
def ocr():
    photo = request.files.get("photo")
    if photo is None or not photo.filename:
        audit(
            "ocr.failed",
            outcome="failure",
            severity="warning",
            reason="missing_file",
        )
        return jsonify(ok=False, reason="missing_file", message="Selecione uma foto."), 400
    text, error = extract_text(photo)
    if error == "ocr_unavailable":
        audit(
            "ocr.failed",
            outcome="failure",
            severity="warning",
            reason="ocr_unavailable",
        )
        return (
            jsonify(
                ok=False,
                reason="ocr_unavailable",
                message="OCR não está instalado neste servidor. A foto pode ser anexada à nota.",
            ),
            503,
        )
    if error:
        audit(
            "ocr.failed",
            outcome="failure",
            severity="warning",
            reason=error,
        )
        return (
            jsonify(
                ok=False,
                reason=error,
                message="Não consegui ler a imagem. Tente outra foto ou digite o trecho.",
            ),
            422,
        )
    audit("ocr.extract", text_length=len(text or ""))
    return jsonify(ok=True, text=text)


@notes_bp.route("/media/notes/<filename>")
@login_required
def note_image(filename: str):
    safe_name = Path(filename).name
    Note.query.filter_by(
        user_id=current_user().id, image_filename=safe_name
    ).first_or_404()
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"], safe_name, max_age=3600
    )


# ---------------------------------------------------------------------------
# Ajustes, backup, exportação
# ---------------------------------------------------------------------------
@settings_bp.route("/settings")
@settings_bp.route("/admin")
@login_required
def index():
    user = current_user()
    profile_form = ProfileForm(obj=user)
    password_form = PasswordForm()
    restore_form = RestoreForm()
    delete_form = DeleteAccountForm()
    stats = _reading_stats(user)
    db_path = None
    try:
        db_path = _sqlite_path()
    except Exception:  # noqa: BLE001 - banco em memória nos testes
        db_path = None

    return render_template(
        "settings.html",
        profile_form=profile_form,
        password_form=password_form,
        restore_form=restore_form,
        delete_form=delete_form,
        stats=stats,
        is_admin=user.is_admin,
        db_path=str(db_path) if db_path else "SQLite",
        ocr_ready=ocr_available(),
    )


@settings_bp.route("/settings/users", methods=["GET", "POST"])
@login_required
@admin_required
def users():
    """Área do administrador para criar novas contas no servidor."""
    form = NewUserForm()
    if form.validate_on_submit():
        email = (form.email.data or "").strip().lower()
        existing = User.query.filter(func.lower(User.email) == email).first()
        if existing is not None:
            audit(
                "user.create_failed",
                outcome="failure",
                severity="warning",
                reason="email_in_use",
                target_email=email,
            )
            flash("Já existe uma conta com este e-mail.", "warning")
        else:
            new_user = User(
                name=(form.name.data or "").strip(),
                email=email,
                password_hash=generate_password_hash(form.password.data),
                theme=Config.DEFAULT_THEME,
                is_admin=bool(form.is_admin.data),
            )
            db.session.add(new_user)
            db.session.commit()
            audit(
                "user.create",
                target_user_id=new_user.id,
                target_email=new_user.email,
                is_admin=bool(new_user.is_admin),
            )
            flash(
                f"Usuário “{new_user.name}” criado. A senha pode ser trocada em Ajustes.",
                "success",
            )
            return redirect(url_for("settings.users"))

    people = User.query.order_by(User.created_at.asc()).all()
    return render_template("users.html", form=form, people=people)


@settings_bp.route("/settings/onboarding/complete", methods=["POST"])
@login_required
def onboarding_complete():
    """Marca o tutorial de primeiro acesso como visto (ou pulado)."""
    user = current_user()
    if not user.onboarding_completed:
        user.onboarding_completed = True
        db.session.commit()
        audit("onboarding.complete")
    return redirect_back("main.dashboard")


@settings_bp.route("/settings/tutorial", methods=["POST"])
@login_required
def tutorial_reset():
    """Permite rever o tutorial a qualquer momento pelos Ajustes."""
    user = current_user()
    user.onboarding_completed = False
    db.session.commit()
    audit("onboarding.reset")
    flash("Tutorial reiniciado. Ele aparece na próxima tela.", "info")
    return redirect(url_for("main.dashboard"))


@settings_bp.route("/settings/profile", methods=["POST"])
@login_required
def profile():
    user = current_user()
    form = ProfileForm()
    if form.validate_on_submit():
        email = (form.email.data or "").strip().lower()
        other = User.query.filter(
            func.lower(User.email) == email, User.id != user.id
        ).first()
        if other:
            audit(
                "settings.profile_failed",
                outcome="failure",
                severity="warning",
                reason="email_in_use",
                target_email=email,
            )
            flash("Este e-mail já pertence a outra conta.", "warning")
        else:
            user.name = (form.name.data or "").strip()
            user.email = email
            db.session.commit()
            audit("settings.profile", email=user.email)
            flash("Perfil atualizado.", "success")
    else:
        flash(_first_error(form), "danger")
    return redirect(url_for("settings.index"))


@settings_bp.route("/settings/password", methods=["POST"])
@login_required
def password():
    user = current_user()
    form = PasswordForm()
    if form.validate_on_submit():
        if not check_password_hash(user.password_hash, form.current_password.data or ""):
            audit(
                "settings.password_failed",
                outcome="failure",
                severity="warning",
                reason="current_password_incorrect",
            )
            flash("A senha atual não confere.", "danger")
        elif check_password_hash(user.password_hash, form.new_password.data or ""):
            audit(
                "settings.password_failed",
                outcome="failure",
                severity="warning",
                reason="same_password",
            )
            flash("A nova senha precisa ser diferente da atual.", "warning")
        else:
            user.password_hash = generate_password_hash(form.new_password.data)
            db.session.commit()
            audit("settings.password")
            flash("Senha alterada.", "success")
    else:
        flash(_first_error(form), "danger")
    return redirect(url_for("settings.index") + "#seguranca")


@settings_bp.route("/settings/theme", methods=["POST"])
@login_required
def theme():
    theme_value = (
        request.form.get("theme")
        or (request.get_json(silent=True) or {}).get("theme")
        or ""
    ).strip()
    if theme_value not in {"light", "dark"}:
        if request.headers.get("X-Requested-With") == "fetch":
            return jsonify(ok=False, error="invalid_theme"), 400
        flash("Tema inválido.", "danger")
        return redirect_back("settings.index")

    user = current_user()
    user.theme = theme_value
    db.session.commit()
    audit("settings.theme", theme=theme_value)

    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify(ok=True, theme=theme_value)
    return redirect_back("settings.index")


@settings_bp.route("/settings/backup")
@login_required
@admin_required
def backup():
    """Baixa um único ZIP com banco, capas, fotos e manifesto."""
    db_path = _sqlite_path()
    if not db_path.exists():
        abort(404)

    backup_dir = Path(current_app.config["BACKUP_FOLDER"])
    backup_dir.mkdir(parents=True, exist_ok=True)
    temp_file = tempfile.NamedTemporaryFile(
        prefix=".leobooks-download-", suffix=".zip", dir=backup_dir, delete=False
    )
    temp_path = Path(temp_file.name)
    temp_file.close()
    try:
        manifest = build_full_backup(
            db_path=db_path,
            covers_dir=Path(current_app.config["COVER_FOLDER"]),
            uploads_dir=Path(current_app.config["UPLOAD_FOLDER"]),
            destination=temp_path,
        )
        size = temp_path.stat().st_size
        audit(
            "backup.download",
            backup_format="zip",
            backup_bytes=size,
            books=manifest["counts"].get("books", 0),
            notes=manifest["counts"].get("notes", 0),
        )
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        response = send_file(
            temp_path,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"leobooks_backup_{stamp}.zip",
        )
        response.call_on_close(lambda: temp_path.unlink(missing_ok=True))
        return response
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _validate_backup_file(path: Path) -> tuple[bool, str]:
    """Compatibilidade: valida um banco SQLite avulso (backup antigo)."""
    return validate_sqlite(path)


def _snapshot_current_database(db_path: Path, destination: Path) -> None:
    source_conn = sqlite3.connect(db_path)
    dest_conn = sqlite3.connect(destination)
    try:
        with dest_conn:
            source_conn.backup(dest_conn)
    finally:
        source_conn.close()
        dest_conn.close()


def _install_database(source: Path, db_path: Path) -> None:
    db.session.remove()
    db.engine.dispose()
    for suffix in ("-wal", "-shm"):
        Path(f"{db_path}{suffix}").unlink(missing_ok=True)
    shutil.copyfile(source, db_path)


def _full_restore(upload, db_path: Path, stamp: str) -> tuple[bool, str]:
    """Valida e instala um ZIP completo; devolve (ok, mensagem)."""
    instance_dir = db_path.parent
    temp_root = Path(tempfile.mkdtemp(prefix=".leobooks-restore-", dir=instance_dir))
    covers_dir = Path(current_app.config["COVER_FOLDER"])
    uploads_dir = Path(current_app.config["UPLOAD_FOLDER"])
    backup_dir = Path(current_app.config["BACKUP_FOLDER"])
    backup_dir.mkdir(parents=True, exist_ok=True)

    old_covers = None
    old_uploads = None
    covers_installed = False
    uploads_installed = False
    safety_db = backup_dir / f"antes_da_restauracao_{stamp}.db"
    safety_zip = backup_dir / f"antes_da_restauracao_{stamp}.zip"

    try:
        archive_path = temp_root / "upload.zip"
        upload.save(archive_path)
        manifest, source_db, source_covers, source_uploads = extract_and_validate(
            archive_path,
            temp_root / "data",
            max_uncompressed_bytes=current_app.config.get(
                "BACKUP_MAX_UNCOMPRESSED_BYTES", 1024 * 1024 * 1024
            ),
        )

        # Cópia de segurança completa antes de tocar no estado atual.
        build_full_backup(
            db_path=db_path,
            covers_dir=covers_dir,
            uploads_dir=uploads_dir,
            destination=safety_zip,
        )
        _snapshot_current_database(db_path, safety_db)
        db.session.remove()
        db.engine.dispose()

        if covers_dir.exists():
            old_covers = instance_dir / f".covers.before_restore_{stamp}"
            covers_dir.rename(old_covers)
        if uploads_dir.exists():
            old_uploads = instance_dir / f".uploads.before_restore_{stamp}"
            uploads_dir.rename(old_uploads)

        shutil.move(str(source_covers), str(covers_dir))
        covers_installed = True
        shutil.move(str(source_uploads), str(uploads_dir))
        uploads_installed = True
        _install_database(source_db, db_path)

        # Só remove a cópia antiga depois de o novo estado estar completo.
        if old_covers is not None:
            shutil.rmtree(old_covers, ignore_errors=True)
        if old_uploads is not None:
            shutil.rmtree(old_uploads, ignore_errors=True)
        return True, f"Backup completo restaurado. Segurança: {safety_zip.name}."
    except BackupError as exc:
        # O estado atual ainda está intacto neste ponto (validação antes da troca).
        if covers_installed and covers_dir.exists():
            shutil.rmtree(covers_dir, ignore_errors=True)
        if uploads_installed and uploads_dir.exists():
            shutil.rmtree(uploads_dir, ignore_errors=True)
        if old_covers is not None and old_covers.exists() and not covers_dir.exists():
            old_covers.rename(covers_dir)
        if old_uploads is not None and old_uploads.exists() and not uploads_dir.exists():
            old_uploads.rename(uploads_dir)
        return False, str(exc)
    except Exception:
        current_app.logger.exception("Falha ao restaurar backup completo")
        # Rollback de diretórios e banco, se a troca já tiver começado.
        if covers_installed and covers_dir.exists():
            shutil.rmtree(covers_dir, ignore_errors=True)
        if uploads_installed and uploads_dir.exists():
            shutil.rmtree(uploads_dir, ignore_errors=True)
        if old_covers is not None and old_covers.exists() and not covers_dir.exists():
            old_covers.rename(covers_dir)
        if old_uploads is not None and old_uploads.exists() and not uploads_dir.exists():
            old_uploads.rename(uploads_dir)
        if safety_db.exists():
            try:
                _install_database(safety_db, db_path)
            except Exception:
                current_app.logger.exception("Falha no rollback do banco")
        return False, "Não foi possível restaurar o backup completo. O estado anterior foi mantido."
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def _legacy_restore(upload, db_path: Path, stamp: str) -> tuple[bool, str]:
    """Restaura um .db antigo, mantendo as capas/fotos atuais."""
    fd, temp_name = tempfile.mkstemp(suffix=".db")
    try:
        with open(fd, "wb") as handle:
            upload.save(handle)
        ok, message = _validate_backup_file(Path(temp_name))
        if not ok:
            return False, message

        backup_dir = Path(current_app.config["BACKUP_FOLDER"])
        backup_dir.mkdir(parents=True, exist_ok=True)
        safety = backup_dir / f"antes_da_restauracao_{stamp}.db"
        _snapshot_current_database(db_path, safety)
        _install_database(Path(temp_name), db_path)
        return True, "Backup antigo do banco restaurado. Capas e fotos atuais foram mantidas."
    finally:
        Path(temp_name).unlink(missing_ok=True)


@settings_bp.route("/settings/restore", methods=["POST"])
@login_required
@admin_required
def restore():
    form = RestoreForm()
    if not form.validate_on_submit():
        flash(_first_error(form), "danger")
        return redirect(url_for("settings.index") + "#dados")

    upload = form.backup.data
    db_path = _sqlite_path()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = (upload.filename or "").lower()

    try:
        if filename.endswith(".zip"):
            ok, message = _full_restore(upload, db_path, stamp)
        else:
            ok, message = _legacy_restore(upload, db_path, stamp)
    except BackupError as exc:
        ok, message = False, str(exc)
    except Exception:
        current_app.logger.exception("Falha ao restaurar backup")
        ok, message = False, "Não foi possível restaurar o backup. O estado anterior foi mantido."

    if not ok:
        audit(
            "backup.restore_failed",
            outcome="failure",
            severity="warning",
            reason="invalid_backup",
        )
        flash(message, "danger")
        return redirect(url_for("settings.index") + "#dados")

    audit("backup.restore", backup_format="zip" if filename.endswith(".zip") else "sqlite")
    session.clear()
    flash(message, "success")
    return redirect(url_for("auth.login"))


@settings_bp.route("/settings/delete-account", methods=["POST"])
@login_required
def delete_account():
    user = current_user()
    form = DeleteAccountForm()
    if not form.validate_on_submit():
        flash(_first_error(form), "danger")
        return redirect(url_for("settings.index") + "#zona-perigo")

    if not check_password_hash(user.password_hash, form.password.data or ""):
        flash("Senha incorreta. A conta não foi excluída.", "danger")
        return redirect(url_for("settings.index") + "#zona-perigo")

    upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
    cover_folder = Path(current_app.config["COVER_FOLDER"])
    deleted_user_id = user.id
    deleted_books = len(user.books)
    deleted_notes = len(user.notes)
    deleted_email = user.email
    for note in user.notes:
        remove_image(upload_folder, note.image_filename)
    for book in user.books:
        remove_image(cover_folder, book.cover_filename)

    was_admin = bool(user.is_admin)
    db.session.delete(user)
    db.session.commit()

    if was_admin:
        successor = User.query.order_by(User.created_at.asc()).first()
        if successor is not None:
            successor.is_admin = True
            db.session.commit()

    audit(
        "account.delete",
        user_id=deleted_user_id,
        user_email=deleted_email,
        books=deleted_books,
        notes=deleted_notes,
        was_admin=was_admin,
    )
    session.clear()
    flash("Sua conta e todos os dados vinculados foram excluídos.", "info")
    return redirect(url_for("auth.register"))


# ---------------------------------------------------------------------------
# Exportação (Markdown / JSON)
# ---------------------------------------------------------------------------
def _notes_markdown(user: User, books: list[Book]) -> str:
    exported_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    lines = [
        f"# Caderno de leitura de {user.name}",
        "",
        f"_Exportado do LeoBooks em {exported_at}._",
        "",
    ]
    for book in sorted(books, key=lambda item: item.title.lower()):
        if book.is_digital:
            progress_text = f"{book.progress_percent}% no livro digital"
            if book.total_pages:
                progress_text += f" (≈ {book.current_page}/{book.total_pages} páginas)"
        else:
            progress_text = f"{book.current_page}/{book.total_pages} páginas"
        lines.extend(
            [
                f"## {book.title}",
                "",
                f"**{book.authors}** · {book.status_label} · {progress_text}",
                "",
            ]
        )
        if not book.notes:
            lines.extend(["_Sem notas registradas._", ""])
            continue
        for note in sorted(book.notes, key=lambda item: item.created_at or datetime.min):
            heading = note.type_label
            if note.location_label:
                heading = f"{heading} · {note.location_label}"
            lines.append(f"### {heading}")
            lines.append("")
            lines.append(note.content.strip())
            lines.append("")
            if note.tags:
                lines.append(" ".join(f"#{tag.name.replace(' ', '-')}" for tag in note.tags))
                lines.append("")
        lines.extend(["---", ""])
    return "\n".join(lines).strip() + "\n"


@settings_bp.route("/export/notes.md")
@login_required
def export_markdown():
    user = current_user()
    payload = _notes_markdown(user, user.books).encode("utf-8")
    audit(
        "export.notes",
        format="markdown",
        books=len(user.books),
        notes=sum(len(book.notes) for book in user.books),
    )
    return send_file(
        io.BytesIO(payload),
        mimetype="text/markdown; charset=utf-8",
        as_attachment=True,
        download_name="leobooks_notas.md",
    )


@settings_bp.route("/export/notes.json")
@login_required
def export_json():
    user = current_user()
    payload = {
        "app": "LeoBooks",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": {"name": user.name},
        "books": [
            {
                "id": book.id,
                "title": book.title,
                "authors": book.authors,
                "publisher": book.publisher,
                "isbn": book.isbn,
                "media_type": book.media_type,
                "total_pages": book.total_pages,
                "current_page": book.current_page,
                "percent_complete": book.percent_complete if book.is_digital else None,
                "status": book.status,
                "notes": [note.to_dict() for note in book.notes],
            }
            for book in user.books
        ],
        "tags": [tag.to_dict() for tag in user.tags],
    }
    data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    audit(
        "export.notes",
        format="json",
        books=len(user.books),
        notes=sum(len(book.notes) for book in user.books),
    )
    return send_file(
        io.BytesIO(data),
        mimetype="application/json; charset=utf-8",
        as_attachment=True,
        download_name="leobooks_notas.json",
    )


@settings_bp.route("/export/books/<book_id>.md")
@login_required
def export_book(book_id: str):
    book = _owned_book(book_id)
    payload = _notes_markdown(current_user(), [book]).encode("utf-8")
    audit(
        "export.book",
        format="markdown",
        book_id=book.id,
        title=book.title,
        notes=len(book.notes),
    )
    safe_title = "".join(
        char if char.isalnum() or char in "-_" else "-" for char in book.title.lower()
    ).strip("-")[:60] or "livro"
    return send_file(
        io.BytesIO(payload),
        mimetype="text/markdown; charset=utf-8",
        as_attachment=True,
        download_name=f"{safe_title}.md",
    )


@main_bp.route("/healthz")
def healthz():
    return Response("ok", mimetype="text/plain")
