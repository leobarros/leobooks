from __future__ import annotations

import io
import zipfile
from pathlib import Path

from PIL import Image

from models import Book, Note, db


def png_bytes(size=(30, 40), color="forestgreen"):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def test_full_backup_restores_database_and_assets(app, auth_client):
    response = auth_client.post(
        "/books/new",
        data={
            "title": "Livro com capa",
            "authors": "Autora",
            "media_type": "PHYSICAL",
            "total_pages": "100",
            "current_page": "0",
            "status": "READING",
            "cover": (png_bytes(), "capa.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        book = Book.query.one()
        book_id = book.id
        cover = book.cover_filename
        assert cover

    note_response = auth_client.post(
        "/notes/new",
        data={
            "book_id": book_id,
            "type": "QUOTE",
            "content": "Uma nota com foto.",
            "chapter": "1",
            "page_number": "10",
            "tags": "teste",
            "photo": (png_bytes(), "pagina.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert note_response.status_code == 200
    with app.app_context():
        note = Note.query.one()
        image = note.image_filename
        assert image

    backup_response = auth_client.get("/settings/backup")
    assert backup_response.status_code == 200
    backup_data = backup_response.data
    with zipfile.ZipFile(io.BytesIO(backup_data)) as archive:
        names = set(archive.namelist())
        assert "leobooks.db" in names
        assert "manifest.json" in names
        assert f"covers/{cover}" in names
        assert f"uploads/{image}" in names

    cover_path = Path(app.config["COVER_FOLDER"]) / cover
    image_path = Path(app.config["UPLOAD_FOLDER"]) / image
    assert cover_path.exists() and image_path.exists()

    # Simula perda dos arquivos e alteração do banco antes da restauração.
    cover_path.unlink()
    image_path.unlink()
    with app.app_context():
        book = db.session.get(Book, book_id)
        book.title = "Alterado antes do restore"
        db.session.commit()

    restore = auth_client.post(
        "/settings/restore",
        data={"backup": (io.BytesIO(backup_data), "backup.zip")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert restore.status_code == 302
    assert "/login" in restore.headers["Location"]

    with app.app_context():
        book = db.session.get(Book, book_id)
        assert book.title == "Livro com capa"
        assert (Path(app.config["COVER_FOLDER"]) / cover).exists()
    with app.app_context():
        note = Note.query.one()
        assert note.content == "Uma nota com foto."
        assert (Path(app.config["UPLOAD_FOLDER"]) / image).exists()


def test_restore_accepts_zip_larger_than_normal_upload_limit(auth_client):
    # 9 MB: acima do MAX_CONTENT_LENGTH normal (8 MB), abaixo do limite do restore.
    payload = b"x" * (9 * 1024 * 1024)
    response = auth_client.post(
        "/settings/restore",
        data={"backup": (io.BytesIO(payload), "grande.zip")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "ZIP de backup válido" in response.get_data(as_text=True)
