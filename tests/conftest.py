from __future__ import annotations

import pytest

from app import create_app
from models import Book, Note, User, db


@pytest.fixture
def app(tmp_path):
    application = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "test-secret",
            "DATA_DIR": tmp_path / "instance",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
            "UPLOAD_FOLDER": tmp_path / "uploads",
            "COVER_FOLDER": tmp_path / "covers",
            "BACKUP_FOLDER": tmp_path / "backups",
            "ENABLE_CSP": False,
            "SAMPLE_BOOK_ENABLED": False,
            "SERVER_NAME": "localhost",
        }
    )
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    response = client.post(
        "/register",
        data={
            "name": "Ana Leitora",
            "email": "ana@example.com",
            "password": "1234",
            "confirm": "1234",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    return client


@pytest.fixture
def book(app, auth_client):
    auth_client.post(
        "/books/new",
        data={
            "title": "O Poder do Hábito",
            "authors": "Charles Duhigg",
            "publisher": "Objetiva",
            "isbn": "9788539002545",
            "total_pages": "408",
            "current_page": "0",
            "status": "READING",
        },
        follow_redirects=True,
    )
    with app.app_context():
        book = Book.query.one()
        return {"id": book.id, "title": book.title}


@pytest.fixture
def csrf_app(tmp_path):
    application = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": True,
            "SECRET_KEY": "csrf-secret",
            "DATA_DIR": tmp_path / "instance",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'csrf.db'}",
            "UPLOAD_FOLDER": tmp_path / "uploads",
            "COVER_FOLDER": tmp_path / "covers",
            "BACKUP_FOLDER": tmp_path / "backups",
            "ENABLE_CSP": True,
            "SAMPLE_BOOK_ENABLED": False,
            "SERVER_NAME": "localhost",
        }
    )
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


