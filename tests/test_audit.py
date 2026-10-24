from __future__ import annotations

import json
import logging

import pytest

from app import create_app
from models import db
from tests.helpers import create_book, create_note, register
from utils.audit import AUDIT_LOGGER_NAME


class AuditHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.events: list[dict] = []

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.events.append(json.loads(record.getMessage()))
        except (TypeError, ValueError):
            pass


@pytest.fixture
def audit_handler():
    logger = logging.getLogger(AUDIT_LOGGER_NAME)
    handler = AuditHandler()
    logger.addHandler(handler)
    yield handler
    logger.removeHandler(handler)


def actions(events, name):
    return [event for event in events if event.get("action") == name]


def test_login_logout_and_failures_are_logged(app, client, audit_handler):
    page = client.get("/login")
    assert page.headers.get("X-Request-ID")

    register(client, name="Auditora", email="auditora@example.com", password="abcd")
    client.post("/logout")
    audit_handler.events.clear()

    response = client.post(
        "/login",
        data={"email": "auditora@example.com", "password": "abcd"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    logins = actions(audit_handler.events, "auth.login")
    assert len(logins) == 1
    event = logins[0]
    assert event["user"] == "auditora@example.com"
    assert event["outcome"] == "success"
    assert event["request_id"]
    assert event["ip"]
    assert event["path"] == "/login"
    assert "password" not in json.dumps(event)

    client.post("/logout")
    assert actions(audit_handler.events, "auth.logout")

    client.post(
        "/login",
        data={"email": "auditora@example.com", "password": "errada"},
        follow_redirects=True,
    )
    failures = actions(audit_handler.events, "auth.login_failed")
    assert len(failures) == 1
    assert failures[0]["outcome"] == "failure"
    assert failures[0]["severity"] == "warning"
    assert failures[0]["attempted_email"] == "auditora@example.com"
    assert "errada" not in json.dumps(failures[0])


def test_book_note_and_progress_events_are_logged(
    app, auth_client, audit_handler
):
    audit_handler.events.clear()
    create_book(
        auth_client,
        title="Livro auditado",
        media_type="DIGITAL",
        total_pages="300",
        current_percent="0",
    )
    with app.app_context():
        from models import Book

        book_id = Book.query.filter_by(title="Livro auditado").one().id

    create_book_events = actions(audit_handler.events, "book.create")
    assert create_book_events
    assert create_book_events[-1]["book_id"] == book_id
    assert create_book_events[-1]["title"] == "Livro auditado"

    create_note(
        auth_client,
        book_id,
        content="conteúdo secreto que não deve ir para o log",
        tags="privado, atenção",
    )
    note_events = actions(audit_handler.events, "note.create")
    assert note_events
    assert note_events[-1]["note_type"] == "QUOTE"
    assert note_events[-1]["tag_count"] == 2
    assert "conteúdo secreto" not in json.dumps(audit_handler.events, ensure_ascii=False)

    auth_client.post(
        f"/books/{book_id}/progress",
        data={"progress_mode": "percent", "percent": "42"},
        follow_redirects=True,
    )
    progress_events = actions(audit_handler.events, "book.progress")
    assert progress_events
    assert progress_events[-1]["mode"] == "percent"
    assert progress_events[-1]["percent"] == 42.0
    assert progress_events[-1]["page"] == 126

    with app.app_context():
        from models import Note

        note_id = Note.query.filter_by(book_id=book_id).one().id
    auth_client.post(f"/notes/{note_id}/delete", follow_redirects=True)
    assert actions(audit_handler.events, "note.delete")

    auth_client.post(f"/books/{book_id}/delete", follow_redirects=True)
    delete_events = actions(audit_handler.events, "book.delete")
    assert delete_events
    assert delete_events[-1]["notes"] == 0


def test_csrf_failure_is_logged_without_tokens(csrf_app, audit_handler):
    client = csrf_app.test_client()
    response = client.post("/register", data={"name": "Sem CSRF"})
    assert response.status_code == 400

    events = actions(audit_handler.events, "security.csrf_failure")
    assert len(events) == 1
    assert events[0]["outcome"] == "denied"
    assert events[0]["severity"] == "warning"
    assert events[0]["request_id"]
    assert "csrf_token" not in events[0]
    assert "csrf_token=" not in json.dumps(events[0]).lower()


def test_optional_audit_file(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "audit-file-test",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'audit.db'}",
            "UPLOAD_FOLDER": tmp_path / "uploads",
            "COVER_FOLDER": tmp_path / "covers",
            "BACKUP_FOLDER": tmp_path / "backups",
            "AUDIT_LOG_PATH": str(tmp_path / "logs" / "audit.log"),
        }
    )
    client = app.test_client()
    register(client, name="Arquivo", email="arquivo@example.com", password="abcd")

    log_file = tmp_path / "logs" / "audit.log"
    assert log_file.exists()
    entries = [
        json.loads(line)
        for line in log_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(entry["action"] == "auth.register" for entry in entries)
    assert "abcd" not in log_file.read_text(encoding="utf-8")
    with app.app_context():
        db.session.remove()
