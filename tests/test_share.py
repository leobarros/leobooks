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
