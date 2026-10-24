from __future__ import annotations

from models import Book, db
from tests.helpers import create_book


def test_digital_book_tracks_percent_without_pages(app, auth_client):
    create_book(
        auth_client,
        media_type="DIGITAL",
        total_pages="",
        current_percent="0",
    )
    with app.app_context():
        book = Book.query.one()
        book_id = book.id
        assert book.media_type == "DIGITAL"
        assert book.total_pages == 0
        assert book.progress_percent == 0

    form_page = auth_client.get("/books/new").get_data(as_text=True)
    assert "Formato de leitura" in form_page
    assert "Livro digital" in form_page

    response = auth_client.post(
        f"/books/{book_id}/progress",
        data={"progress_mode": "percent", "percent": "42"},
        follow_redirects=True,
    )
    html = response.get_data(as_text=True)
    assert "Progresso (%)" in html
    assert "42% no livro digital" in html
    with app.app_context():
        book = db.session.get(Book, book_id)
        assert book.progress_percent == 42
        assert book.current_page == 0
        assert book.percent_complete == 42.0
        assert book.status == "READING"

    auth_client.post(
        f"/books/{book_id}/progress",
        data={"progress_mode": "percent", "percent": "100"},
        follow_redirects=True,
    )
    with app.app_context():
        book = db.session.get(Book, book_id)
        assert book.status == "READ"
        assert book.progress_percent == 100


def test_physical_book_tracks_page_and_has_no_digital_panel(app, auth_client):
    create_book(
        auth_client,
        media_type="PHYSICAL",
        total_pages="300",
        current_page="0",
    )
    with app.app_context():
        book_id = Book.query.one().id

    response = auth_client.post(
        f"/books/{book_id}/progress",
        data={"progress_mode": "page", "current_page": "42"},
        follow_redirects=True,
    )
    html = response.get_data(as_text=True)
    assert "Progresso de leitura" in html
    assert "Página atual" in html
    assert "name=\"percent\"" not in html
    with app.app_context():
        book = db.session.get(Book, book_id)
        assert book.media_type == "PHYSICAL"
        assert book.current_page == 42
        assert book.progress_percent == 14
        assert book.percent_complete == 0.0


def test_changing_book_format_converts_progress(app, auth_client):
    create_book(
        auth_client,
        media_type="PHYSICAL",
        total_pages="300",
        current_page="30",
    )
    with app.app_context():
        book_id = Book.query.one().id

    response = auth_client.post(
        f"/books/{book_id}/edit",
        data={
            "title": "O Poder do Hábito",
            "authors": "Charles Duhigg",
            "publisher": "Objetiva",
            "isbn": "9788539002545",
            "media_type": "DIGITAL",
            "total_pages": "300",
            "current_percent": "0",
            "status": "READING",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        book = db.session.get(Book, book_id)
        assert book.media_type == "DIGITAL"
        assert book.progress_percent == 10
        assert book.current_page == 30

    auth_client.post(
        f"/books/{book_id}/edit",
        data={
            "title": "O Poder do Hábito",
            "authors": "Charles Duhigg",
            "publisher": "Objetiva",
            "isbn": "9788539002545",
            "media_type": "PHYSICAL",
            "total_pages": "300",
            "current_page": "0",
            "status": "READING",
        },
        follow_redirects=True,
    )
    with app.app_context():
        book = db.session.get(Book, book_id)
        assert book.media_type == "PHYSICAL"
        assert book.current_page == 30
        assert book.progress_percent == 10
        assert book.percent_complete == 0.0
