from __future__ import annotations

import io

from PIL import Image

from models import Book, Note, db
from tests.helpers import create_book, create_note, register


def png_bytes(size=(60, 90), color="tomato"):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def test_create_book_redirects_to_detail(app, auth_client):
    response = create_book(auth_client)
    assert response.status_code == 200
    assert "O Poder do Hábito" in response.get_data(as_text=True)
    with app.app_context():
        book = Book.query.one()
        assert book.title == "O Poder do Hábito"
        assert book.status == "READING"
        assert book.total_pages == 408


def test_book_validation_rejects_invalid_pages(auth_client):
    response = create_book(auth_client, total_pages="0")
    assert response.status_code == 200
    assert "Páginas totais" in response.get_data(as_text=True)

    response = create_book(auth_client, total_pages="100", current_page="200")
    assert "não pode passar do total" in response.get_data(as_text=True)


def test_book_validation_rejects_invalid_isbn(auth_client):
    response = create_book(auth_client, isbn="abc")
    assert "ISBN inválido" in response.get_data(as_text=True)


def test_update_book_and_cover_upload(app, auth_client):
    create_book(auth_client)
    with app.app_context():
        book_id = Book.query.one().id

    response = auth_client.post(
        f"/books/{book_id}/edit",
        data={
            "title": "Novo título",
            "authors": "Nova autora",
            "publisher": "Editora",
            "isbn": "9788539002545",
            "total_pages": "300",
            "current_page": "30",
            "status": "READING",
            "cover": (png_bytes(), "capa.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Novo título" in html
    assert "/media/covers/" in html
    with app.app_context():
        book = db.session.get(Book, book_id)
        assert book.cover_filename and book.cover_filename.endswith(".jpg")
        cover_path = __import__("pathlib").Path(app.config["COVER_FOLDER"]) / book.cover_filename
        assert cover_path.exists()

    cover_response = auth_client.get(f"/media/covers/{book.cover_filename}")
    assert cover_response.status_code == 200
    assert cover_response.mimetype == "image/jpeg"


def test_progress_can_complete_book(app, auth_client):
    create_book(auth_client, total_pages="100")
    with app.app_context():
        book_id = Book.query.one().id

    response = auth_client.post(
        f"/books/{book_id}/progress", data={"current_page": "100"}, follow_redirects=True
    )
    assert "concluiu o livro" in response.get_data(as_text=True)
    with app.app_context():
        book = db.session.get(Book, book_id)
        assert book.current_page == 100
        assert book.progress_percent == 100
        assert book.status == "READ"


def test_progress_rejects_out_of_range(app, auth_client):
    create_book(auth_client, total_pages="100", current_page="10")
    with app.app_context():
        book_id = Book.query.one().id

    response = auth_client.post(
        f"/books/{book_id}/progress", data={"current_page": "999"}, follow_redirects=True
    )
    assert "Página inválida" in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Book, book_id).current_page == 10


def test_status_endpoint(app, auth_client):
    create_book(auth_client)
    with app.app_context():
        book_id = Book.query.one().id

    auth_client.post(f"/books/{book_id}/status", data={"status": "READ"}, follow_redirects=True)
    with app.app_context():
        book = db.session.get(Book, book_id)
        assert book.status == "READ"
        assert book.current_page == book.total_pages

    auth_client.post(f"/books/{book_id}/status", data={"status": "INVALID"}, follow_redirects=True)
    with app.app_context():
        assert db.session.get(Book, book_id).status == "READ"


def test_generated_cover_is_svg_and_escaped(app, auth_client):
    create_book(auth_client, title="<script>alert(1)</script>", authors="Autora <b>")
    with app.app_context():
        book_id = Book.query.one().id

    response = auth_client.get(f"/books/{book_id}/cover.svg")
    assert response.status_code == 200
    assert response.mimetype == "image/svg+xml"
    body = response.get_data(as_text=True)
    assert body.startswith("<svg")
    assert "<script>alert" not in body
    assert "&lt;script&gt;" in body


def test_delete_book_cascades_notes(app, auth_client):
    create_book(auth_client)
    with app.app_context():
        book_id = Book.query.one().id
    auth_client.post(
        "/notes/new",
        data={"book_id": book_id, "type": "QUOTE", "content": "nota para apagar"},
        follow_redirects=True,
    )

    auth_client.post(f"/books/{book_id}/delete", follow_redirects=True)
    with app.app_context():
        assert Book.query.count() == 0
        assert Note.query.count() == 0


def test_library_filters_and_search(app, auth_client):
    create_book(auth_client, title="Livro em leitura", status="READING")
    create_book(auth_client, title="Livro na fila", status="WANT_TO_READ")
    create_book(auth_client, title="Livro terminado", status="READ", current_page="408")

    def card_title(title):
        return f'aria-label="Abrir {title}"'

    reading = auth_client.get("/library?status=READING").get_data(as_text=True)
    assert card_title("Livro em leitura") in reading
    assert card_title("Livro na fila") not in reading

    finished = auth_client.get("/library?status=READ").get_data(as_text=True)
    assert card_title("Livro terminado") in finished

    searched = auth_client.get("/library?q=Livro+terminado").get_data(as_text=True)
    assert card_title("Livro terminado") in searched
    assert card_title("Livro na fila") not in searched

    sorted_by_title = auth_client.get("/library?sort=title").get_data(as_text=True)
    assert sorted_by_title.index(card_title("Livro em leitura")) < sorted_by_title.index(card_title("Livro na fila"))


def test_book_isolation_for_mutations(app, auth_client):
    create_book(auth_client)
    with app.app_context():
        book_id = Book.query.one().id

    other = app.test_client()
    register(other, email="outra@example.com", password="zzzz")

    assert other.post(f"/books/{book_id}/progress", data={"current_page": "50"}).status_code == 404
    assert other.post(f"/books/{book_id}/delete").status_code == 404
    assert other.post(f"/books/{book_id}/status", data={"status": "READ"}).status_code == 404
    assert other.get(f"/books/{book_id}/edit").status_code == 404


def test_progress_uses_digital_percentage(app, auth_client):
    create_book(
        auth_client,
        media_type="DIGITAL",
        total_pages="300",
        current_percent="0",
    )
    with app.app_context():
        book_id = Book.query.one().id

    response = auth_client.post(
        f"/books/{book_id}/progress",
        data={"progress_mode": "percent", "percent": "42"},
        follow_redirects=True,
    )
    html = response.get_data(as_text=True)
    assert "42% no livro digital (≈ página 126 de 300)" in html
    with app.app_context():
        book = db.session.get(Book, book_id)
        assert book.current_page == 126
        assert book.progress_percent == 42
        assert book.status == "READING"

    response = auth_client.post(
        f"/books/{book_id}/progress",
        data={"progress_mode": "percent", "percent": "100"},
        follow_redirects=True,
    )
    assert "concluiu o livro" in response.get_data(as_text=True)
    with app.app_context():
        book = db.session.get(Book, book_id)
        assert book.current_page == 300
        assert book.status == "READ"


def test_progress_rejects_invalid_digital_percentage(app, auth_client):
    create_book(
        auth_client,
        media_type="DIGITAL",
        total_pages="300",
        current_percent="42",
    )
    with app.app_context():
        book_id = Book.query.one().id

    response = auth_client.post(
        f"/books/{book_id}/progress",
        data={"progress_mode": "percent", "percent": "101"},
        follow_redirects=True,
    )
    assert "percentual entre 0 e 100" in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Book, book_id).current_page == 126
        assert db.session.get(Book, book_id).percent_complete == 42.0
