from __future__ import annotations

from models import Book
from tests.helpers import create_book, create_note


def test_review_share_button_carries_filename_context(app, auth_client):
    create_book(
        auth_client,
        title="O Príncipe",
        authors="Nicolau Maquiavel",
        total_pages="128",
    )
    with app.app_context():
        book_id = Book.query.one().id
    create_note(
        auth_client,
        book_id,
        content="Uma citação para compartilhar.",
        chapter="Capítulo XXI",
        page_number="74",
    )

    html = auth_client.get("/review").get_data(as_text=True)
    assert 'data-share-book="O Príncipe"' in html
    assert 'data-share-chapter="Capítulo XXI"' in html
    assert 'data-share-page="74"' in html
    assert "Compartilhar como imagem" in html


def test_shared_quote_image_does_not_show_site_address():
    from pathlib import Path

    source = (Path(__file__).resolve().parent.parent / "static/js/app.js").read_text(
        encoding="utf-8"
    )
    assert "leobooks.local" not in source


def test_review_random_next_excludes_current_quote(app, auth_client, book):
    from models import Note

    create_note(auth_client, book["id"], content="Primeira citação.")
    create_note(auth_client, book["id"], content="Segunda citação.")
    with app.app_context():
        ids = [note.id for note in Note.query.order_by(Note.created_at.asc()).all()]
        first_id, second_id = ids

    page = auth_client.get(f"/review?exclude={first_id}").get_data(as_text=True)
    assert "Segunda citação." in page
    assert "Primeira citação." not in page

    same_page = auth_client.get(f"/review?exclude={second_id}").get_data(as_text=True)
    assert "Primeira citação." in same_page
