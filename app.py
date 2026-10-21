"""LeoBooks — aplicação WSGI (Flask) de notas, resumos e citações de leitura."""

from __future__ import annotations

import os
import secrets
import time
from datetime import date
from pathlib import Path

from flask import Flask, g, redirect, render_template, url_for
from flask_wtf.csrf import CSRFError, CSRFProtect

from config import Config
from forms import NoteForm
from helpers import (
    admin_required,
    current_user,
    greeting_for_now,
    register_template_helpers,
    weekday_long,
)
from models import BOOK_STATUSES, NOTE_TYPES, Book, db
from routes import auth_bp, books_bp, main_bp, notes_bp, settings_bp
from utils.audit import audit, configure_audit_logging
from utils.ocr import ocr_available

csrf = CSRFProtect()


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)

    # --- Logs estruturados -------------------------------------------------
    configure_audit_logging(app)

    # --- Diretórios persistentes ------------------------------------------
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    for key in ("UPLOAD_FOLDER", "COVER_FOLDER", "BACKUP_FOLDER"):
        Path(app.config[key]).mkdir(parents=True, exist_ok=True)

    database_uri = str(app.config.get("SQLALCHEMY_DATABASE_URI", ""))
    if database_uri.startswith("sqlite:///") and ":memory:" not in database_uri:
        Path(database_uri.replace("sqlite:///", "", 1)).parent.mkdir(
            parents=True, exist_ok=True
        )

    # --- Contexto da requisição para logs/segurança ------------------------
    # Registrado antes do CSRFProtect para que falhas de CSRF também tenham
    # request_id, IP e duração nos logs.
    @app.before_request
    def _request_context():
        g.csp_nonce = secrets.token_urlsafe(16)
        g.request_id = secrets.token_hex(6)
        g.request_started = time.perf_counter()

    # --- Extensões ---------------------------------------------------------
    db.init_app(app)
    csrf.init_app(app)
    register_template_helpers(app)

    # --- Blueprints --------------------------------------------------------
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(books_bp)
    app.register_blueprint(notes_bp)
    app.register_blueprint(settings_bp)

    # --- Contexto global dos templates ------------------------------------
    @app.context_processor
    def inject_layout_context():
        user = current_user()
        context = {
            "current_user": user,
            "csp_nonce": getattr(g, "csp_nonce", ""),
            "note_types": NOTE_TYPES,
            "book_statuses": BOOK_STATUSES,
            "greeting": greeting_for_now(),
            "today": date.today(),
            "weekday": weekday_long(),
            "app_name": "LeoBooks",
            "quick_note_form": None,
            "quick_books": [],
            "tag_suggestions": [],
            "ocr_available": ocr_available(),
        }
        if user is not None:
            try:
                books = (
                    Book.query.filter_by(user_id=user.id)
                    .order_by(Book.updated_at.desc())
                    .all()
                )
                form = NoteForm()
                form.book_id.choices = [
                    (book.id, f"{book.title} — {book.authors}") for book in books
                ]
                context.update(
                    {
                        "quick_note_form": form,
                        "quick_books": books,
                        "tag_suggestions": sorted(
                            {tag.name for tag in user.tags}, key=str.casefold
                        ),
                    }
                )
            except Exception:  # pragma: no cover - não derruba a página
                app.logger.exception("Falha ao montar o contexto de navegação")
        return context

    # --- Segurança: cabeçalhos e CSP --------------------------------------
    @app.after_request
    def _security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        response.headers.setdefault(
            "Permissions-Policy", "camera=(self), microphone=(), geolocation=()"
        )
        if getattr(g, "request_id", None):
            response.headers.setdefault("X-Request-ID", g.request_id)
        if app.config.get("ENABLE_CSP", True):
            nonce = getattr(g, "csp_nonce", "")
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'self'; base-uri 'self'; frame-ancestors 'self'; "
                "form-action 'self'; object-src 'none'; "
                f"script-src 'self' 'nonce-{nonce}'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob: https: http:; "
                "font-src 'self'; connect-src 'self'",
            )
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response

    # --- Páginas de erro ---------------------------------------------------
    def _error_page(code: int, title: str, message: str):
        return (
            render_template(
                "errors/error.html", code=code, title=title, message=message
            ),
            code,
        )

    @app.errorhandler(400)
    def _bad_request(error):  # noqa: ANN001
        audit("http.bad_request", outcome="failure", severity="warning")
        return _error_page(400, "Pedido inválido", "Não conseguimos entender esta solicitação.")

    @app.errorhandler(CSRFError)
    def _csrf_error(error):  # noqa: ANN001
        audit(
            "security.csrf_failure",
            outcome="denied",
            severity="warning",
            reason="csrf_token_invalid_or_expired",
        )
        return _error_page(
            400,
            "Sessão expirada",
            "O formulário perdeu a validade. Recarregue a página e tente novamente.",
        )

    @app.errorhandler(403)
    def _forbidden(error):  # noqa: ANN001
        audit("security.access_denied", outcome="denied", severity="warning")
        return _error_page(403, "Acesso restrito", "Você não tem permissão para este conteúdo.")

    @app.errorhandler(404)
    def _not_found(error):  # noqa: ANN001
        return _error_page(
            404,
            "Página fora da estante",
            "O endereço não existe ou o conteúdo foi removido.",
        )

    @app.errorhandler(413)
    def _too_large(error):  # noqa: ANN001
        audit(
            "http.payload_too_large",
            outcome="failure",
            severity="warning",
            limit_bytes=app.config.get("MAX_CONTENT_LENGTH"),
        )
        return _error_page(
            413,
            "Arquivo grande demais",
            "O limite de upload é de 8 MB. Envie uma imagem menor.",
        )

    @app.errorhandler(500)
    def _server_error(error):  # noqa: ANN001
        db.session.rollback()
        app.logger.exception("Erro interno", exc_info=error)
        audit(
            "error.server",
            outcome="failure",
            severity="error",
            error_type=type(error).__name__,
        )
        return _error_page(
            500,
            "Um tropeço na leitura",
            "Algo falhou do nosso lado. Tente novamente em instantes.",
        )

    # --- Banco -------------------------------------------------------------
    with app.app_context():
        db.create_all()
        _ensure_admin_column()
        _ensure_onboarding_column()
        _ensure_an_admin_exists()

    return app


def log_app_start() -> None:
    """Registra a inicialização efetiva do servidor (não em CLI/testes)."""
    audit(
        "app.start",
        database=str(app.config.get("SQLALCHEMY_DATABASE_URI", "")),
        host=app.config.get("HOST"),
        port=app.config.get("PORT"),
        debug=bool(app.config.get("DEBUG")),
        cover_lookup=bool(app.config.get("COVER_LOOKUP_ENABLED", True)),
        audit_log_path=app.config.get("AUDIT_LOG_PATH") or None,
        pid=os.getpid(),
    )


def _ensure_admin_column() -> None:
    """Migração leve para bancos criados antes do papel de administrador."""
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if "users" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "is_admin" not in columns:
        db.session.execute(
            text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0")
        )
        db.session.commit()


def _ensure_onboarding_column() -> None:
    """Migração leve para bancos criados antes do onboarding."""
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if "users" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "onboarding_completed" not in columns:
        db.session.execute(
            text(
                "ALTER TABLE users ADD COLUMN onboarding_completed "
                "BOOLEAN NOT NULL DEFAULT 0"
            )
        )
        db.session.commit()


def _ensure_an_admin_exists() -> None:
    """Garante que o caderno tenha ao menos um administrador capaz de fazer backup."""
    from models import User

    if User.query.filter_by(is_admin=True).first() is not None:
        return
    first_user = User.query.order_by(User.created_at.asc()).first()
    if first_user is not None:
        first_user.is_admin = True
        db.session.commit()


app = create_app()


if __name__ == "__main__":
    port = int(app.config["PORT"])
    host = app.config["HOST"]
    log_app_start()
    print(f"\n  LeoBooks · caderno de leitura\n  http://{host}:{port}\n", flush=True)
    app.run(host=host, port=port, debug=bool(app.config["DEBUG"]))
