from __future__ import annotations

import io
import json

from models import Book, Note, Tag, User, db
from tests.helpers import create_book, create_note, register


def test_settings_and_admin_pages_render(auth_client):
    settings = auth_client.get("/settings")
    assert settings.status_code == 200
    assert "Aparência" in settings.get_data(as_text=True)
    assert "Zona de perigo" in settings.get_data(as_text=True)

    admin = auth_client.get("/admin")
    assert admin.status_code == 200


def test_theme_is_persisted(app, auth_client):
    response = auth_client.post(
        "/settings/theme",
        json={"theme": "dark"},
        headers={"X-Requested-With": "fetch", "Accept": "application/json"},
    )
    assert response.status_code == 200
    assert response.get_json() == {"ok": True, "theme": "dark"}
    with app.app_context():
        assert User.query.one().theme == "dark"

    html = auth_client.get("/").get_data(as_text=True)
    assert 'data-bs-theme="dark"' in html

    invalid = auth_client.post(
        "/settings/theme",
        json={"theme": "neon"},
        headers={"X-Requested-With": "fetch"},
    )
    assert invalid.status_code == 400


def test_profile_update_and_duplicate_email(app, auth_client):
    register(app.test_client(), name="Outra", email="ocupado@example.com")
    response = auth_client.post(
        "/settings/profile",
        data={"name": "Ana Nova", "email": "ocupado@example.com"},
        follow_redirects=True,
    )
    assert "já pertence a outra conta" in response.get_data(as_text=True)
    with app.app_context():
        assert User.query.filter_by(email="ana@example.com").one().name == "Ana Leitora"

    response = auth_client.post(
        "/settings/profile",
        data={"name": "Ana Nova", "email": "ana@example.com"},
        follow_redirects=True,
    )
    assert "Perfil atualizado" in response.get_data(as_text=True)
    with app.app_context():
        assert User.query.filter_by(email="ana@example.com").one().name == "Ana Nova"


def test_change_password_rules_and_login(app, auth_client):
    wrong = auth_client.post(
        "/settings/password",
        data={"current_password": "errada", "new_password": "efgh", "confirm": "efgh"},
        follow_redirects=True,
    )
    assert "não confere" in wrong.get_data(as_text=True)

    too_long = auth_client.post(
        "/settings/password",
        data={"current_password": "1234", "new_password": "12345678901", "confirm": "12345678901"},
        follow_redirects=True,
    )
    assert "entre 4 e 10 caracteres" in too_long.get_data(as_text=True)

    changed = auth_client.post(
        "/settings/password",
        data={"current_password": "1234", "new_password": "efgh", "confirm": "efgh"},
        follow_redirects=True,
    )
    assert "Senha alterada" in changed.get_data(as_text=True)

    auth_client.post("/logout")
    response = auth_client.post(
        "/login",
        data={"email": "ana@example.com", "password": "efgh"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Boa" in response.get_data(as_text=True) or "Bom" in response.get_data(as_text=True)


def test_exports_markdown_and_json(auth_client, book):
    create_note(auth_client, book["id"], content="Trecho exportável", tags="atenção")
    markdown = auth_client.get("/export/notes.md")
    assert markdown.status_code == 200
    assert "text/markdown" in markdown.mimetype
    assert "Trecho exportável" in markdown.get_data(as_text=True)
    assert "attachment" in markdown.headers["Content-Disposition"]

    payload = auth_client.get("/export/notes.json")
    assert payload.status_code == 200
    data = json.loads(payload.get_data(as_text=True))
    assert data["app"] == "LeoBooks"
    assert data["books"][0]["notes"][0]["content"] == "Trecho exportável"
    assert "password" not in json.dumps(data)

    per_book = auth_client.get(f"/export/books/{book['id']}.md")
    assert per_book.status_code == 200
    assert "Trecho exportável" in per_book.get_data(as_text=True)


def test_backup_download_is_sqlite(auth_client):
    response = auth_client.get("/settings/backup")
    assert response.status_code == 200
    assert response.data.startswith(b"SQLite format 3\x00")
    assert "attachment" in response.headers["Content-Disposition"]


def test_restore_rejects_invalid_file(auth_client):
    response = auth_client.post(
        "/settings/restore",
        data={"backup": (io.BytesIO(b"nao e um banco"), "falso.db")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "não é um banco SQLite válido" in response.get_data(as_text=True)


def test_restore_valid_backup_ends_session(app, auth_client):
    backup = auth_client.get("/settings/backup").data
    response = auth_client.post(
        "/settings/restore",
        data={"backup": (io.BytesIO(backup), "backup.db")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert auth_client.get("/").status_code == 302
    assert auth_client.get("/login").status_code == 200


def test_delete_account_requires_confirmation_and_cascades(app, auth_client, book):
    create_note(auth_client, book["id"], content="some com a conta")

    wrong = auth_client.post(
        "/settings/delete-account",
        data={"password": "1234", "confirmation": "talvez"},
        follow_redirects=True,
    )
    assert "EXCLUIR" in wrong.get_data(as_text=True)

    wrong_password = auth_client.post(
        "/settings/delete-account",
        data={"password": "errada", "confirmation": "EXCLUIR"},
        follow_redirects=True,
    )
    assert "Senha incorreta" in wrong_password.get_data(as_text=True)

    deleted = auth_client.post(
        "/settings/delete-account",
        data={"password": "1234", "confirmation": "EXCLUIR"},
        follow_redirects=True,
    )
    assert deleted.status_code == 200
    assert "excluídos" in deleted.get_data(as_text=True)
    with app.app_context():
        assert User.query.count() == 0
        assert Book.query.count() == 0
        assert Note.query.count() == 0
        assert Tag.query.count() == 0


def test_only_admin_can_download_and_restore_backup(app, auth_client):
    other = app.test_client()
    register(other, name="Comum", email="comum@example.com", password="zzzz")
    assert other.get("/settings/backup").status_code == 403
    assert other.post(
        "/settings/restore",
        data={"backup": (io.BytesIO(b"SQLite format 3\x00"), "qualquer.db")},
        content_type="multipart/form-data",
    ).status_code == 403

    settings = other.get("/settings").get_data(as_text=True)
    assert "Backup do servidor" in settings
    assert "/settings/backup" not in settings


def test_first_registered_user_is_admin(app, client):
    register(client, name="Primeira", email="primeira@example.com", password="1234")
    register(app.test_client(), name="Segunda", email="segunda@example.com", password="1234")
    with app.app_context():
        first = User.query.filter_by(email="primeira@example.com").one()
        second = User.query.filter_by(email="segunda@example.com").one()
        assert first.is_admin is True
        assert second.is_admin is False


def test_admin_deletion_promotes_successor(app, auth_client):
    other = app.test_client()
    register(other, name="Sucessora", email="sucessora@example.com", password="zzzz")
    with app.app_context():
        younger = User.query.filter_by(email="sucessora@example.com").one()
        assert younger.is_admin is False

    auth_client.post(
        "/settings/delete-account",
        data={"password": "1234", "confirmation": "EXCLUIR"},
        follow_redirects=True,
    )
    with app.app_context():
        successor = User.query.filter_by(email="sucessora@example.com").one()
        assert successor.is_admin is True
