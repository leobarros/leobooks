from __future__ import annotations

import io

from PIL import Image

from models import Book, Note, Tag, db
from tests.helpers import create_book, create_note, register


def png_bytes():
    buffer = io.BytesIO()
    Image.new("RGB", (80, 120), "navy").save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def test_create_note_with_tags_and_sanitized_markdown(app, auth_client, book):
    response = create_note(
        auth_client,
        book["id"],
        content="**Loop** do hábito <script>alert(1)</script>",
        tags="hábito, atenção",
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "<strong>Loop</strong>" in html
    assert "<script>alert" not in html

    with app.app_context():
        note = Note.query.one()
        assert note.type == "QUOTE"
        assert note.page_number == 42
        assert note.chapter == "2"
        assert {tag.name for tag in note.tags} == {"hábito", "atenção"}
        assert Tag.query.count() == 2


def test_create_note_rejects_empty_content(app, auth_client, book):
    response = auth_client.post(
        "/notes/new",
        data={"book_id": book["id"], "type": "QUOTE", "content": "   "},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Escreva a nota" in response.get_data(as_text=True)
    with app.app_context():
        assert Note.query.count() == 0


def test_cannot_create_note_on_another_users_book(app, auth_client):
    other = app.test_client()
    register(other, name="Dona", email="dona@example.com", password="zzzz")
    create_book(other, title="Livro alheio")
    with app.app_context():
        foreign_book_id = Book.query.one().id

    response = auth_client.post(
        "/notes/new",
        data={"book_id": foreign_book_id, "type": "QUOTE", "content": "invasão"},
    )
    assert response.status_code in (302, 404)
    with app.app_context():
        assert Note.query.count() == 0


def test_edit_note_changes_type_tags_and_content(app, auth_client, book):
    create_note(auth_client, book["id"], content="Original", note_type="QUOTE", tags="atenção")
    with app.app_context():
        note_id = Note.query.one().id

    response = auth_client.post(
        f"/notes/{note_id}/edit",
        data={
            "book_id": book["id"],
            "type": "SUMMARY",
            "content": "## Novo resumo\n\n- ponto",
            "chapter": "4",
            "page_number": "55",
            "tags": "método, foco",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        note = db.session.get(Note, note_id)
        assert note.type == "SUMMARY"
        assert note.chapter == "4"
        assert note.page_number == 55
        assert {tag.name for tag in note.tags} == {"método", "foco"}


def test_delete_note(app, auth_client, book):
    create_note(auth_client, book["id"])
    with app.app_context():
        note_id = Note.query.one().id

    auth_client.post(f"/notes/{note_id}/delete", follow_redirects=True)
    with app.app_context():
        assert Note.query.count() == 0


def test_note_filter_tabs_by_type(auth_client, book):
    create_note(auth_client, book["id"], content="conteudo-citacao", note_type="QUOTE", tags="")
    create_note(auth_client, book["id"], content="conteudo-resumo", note_type="SUMMARY", tags="")
    create_note(auth_client, book["id"], content="conteudo-insight", note_type="INSIGHT", tags="")

    quotes = auth_client.get(f"/books/{book['id']}?type=QUOTE").get_data(as_text=True)
    assert "conteudo-citacao" in quotes
    assert "conteudo-resumo" not in quotes

    summaries = auth_client.get(f"/books/{book['id']}?type=SUMMARY").get_data(as_text=True)
    assert "conteudo-resumo" in summaries
    assert "conteudo-insight" not in summaries


def test_note_photo_is_private(app, auth_client, book):
    auth_client.post(
        "/notes/new",
        data={
            "book_id": book["id"],
            "type": "QUOTE",
            "content": "Com foto",
            "chapter": "1",
            "page_number": "5",
            "tags": "",
            "photo": (png_bytes(), "pagina.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    with app.app_context():
        note = Note.query.one()
        assert note.image_filename and note.image_filename.endswith(".jpg")
        filename = note.image_filename

    response = auth_client.get(f"/media/notes/{filename}")
    assert response.status_code == 200

    other = app.test_client()
    register(other, email="curiosa@example.com", password="zzzz")
    assert other.get(f"/media/notes/{filename}").status_code == 404


def test_note_rejects_non_image_upload(app, auth_client, book):
    response = auth_client.post(
        "/notes/new",
        data={
            "book_id": book["id"],
            "type": "QUOTE",
            "content": "Arquivo estranho",
            "photo": (io.BytesIO(b"not an image"), "pagina.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "não é uma imagem válida" in response.get_data(as_text=True)
    with app.app_context():
        assert Note.query.count() == 0


def test_ocr_endpoint_missing_file(auth_client):
    response = auth_client.post("/notes/ocr")
    assert response.status_code == 400
    assert response.get_json()["reason"] == "missing_file"


def test_ocr_endpoint_success_and_unavailable(monkeypatch, auth_client):
    import routes

    monkeypatch.setattr(routes, "extract_text", lambda photo: ("Texto da página", None))
    response = auth_client.post(
        "/notes/ocr",
        data={"photo": (png_bytes(), "pagina.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert response.get_json() == {"ok": True, "text": "Texto da página"}

    monkeypatch.setattr(routes, "extract_text", lambda photo: ("", "ocr_unavailable"))
    response = auth_client.post(
        "/notes/ocr",
        data={"photo": (png_bytes(), "pagina.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 503
    assert response.get_json()["reason"] == "ocr_unavailable"


def test_notes_are_isolated_between_books_and_users(app, auth_client, book):
    create_note(auth_client, book["id"], content="segredo")
    with app.app_context():
        note_id = Note.query.one().id

    other = app.test_client()
    register(other, email="outra@example.com", password="zzzz")
    assert other.post(
        f"/notes/{note_id}/edit",
        data={"book_id": book["id"], "type": "QUOTE", "content": "alterado"},
    ).status_code == 404
    assert other.post(f"/notes/{note_id}/delete").status_code == 404


def test_orphan_tags_are_cleaned(app, auth_client, book):
    create_note(auth_client, book["id"], content="com tag", tags="efêmera")
    with app.app_context():
        note_id = Note.query.one().id
        assert Tag.query.filter_by(name="efêmera").count() == 1

    auth_client.post(
        f"/notes/{note_id}/edit",
        data={
            "book_id": book["id"],
            "type": "QUOTE",
            "content": "sem tag",
            "chapter": "",
            "page_number": "",
            "tags": "",
        },
        follow_redirects=True,
    )
    with app.app_context():
        assert Tag.query.filter_by(name="efêmera").count() == 0

    create_note(auth_client, book["id"], content="outra", tags="descartável")
    with app.app_context():
        note_id = Note.query.filter_by(content="outra").one().id
    auth_client.post(f"/notes/{note_id}/delete", follow_redirects=True)
    with app.app_context():
        assert Tag.query.filter_by(name="descartável").count() == 0
