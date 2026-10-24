from __future__ import annotations

from tests.helpers import create_book, create_note


def test_library_search_ignores_accents_in_title_and_author(app, auth_client):
    create_book(
        auth_client,
        title="O Príncipe",
        authors="Nicolau Maquiavel",
        total_pages="128",
    )

    by_title = auth_client.get("/library?q=principe").get_data(as_text=True)
    assert "O Príncipe" in by_title

    by_author = auth_client.get("/library?q=maquiavel").get_data(as_text=True)
    assert "O Príncipe" in by_author


def test_global_search_ignores_accents_in_book_and_note(app, auth_client):
    create_book(
        auth_client,
        title="O Príncipe",
        authors="Nicolau Maquiavel",
        total_pages="128",
    )
    from tests.helpers import create_book as _create_book  # noqa: F401
    from models import Book

    with app.app_context():
        book_id = Book.query.one().id
    create_note(
        auth_client,
        book_id,
        content="Uma nota sobre política e poder.",
    )

    by_book = auth_client.get("/search?q=principe").get_data(as_text=True)
    assert "O Príncipe" in by_book

    by_note = auth_client.get("/search?q=politica").get_data(as_text=True)
    assert "Uma nota sobre política e poder." in by_note


def test_note_modal_button_uses_salvar(auth_client):
    create_book(auth_client, title="Livro com nota", authors="Autora")
    html = auth_client.get("/").get_data(as_text=True)
    assert "Salvar" in html
    assert "Guardar nota" not in html
