from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

import routes
from utils import book_lookup as lookup
from utils.book_lookup import CoverLookupError
from tests.helpers import create_book


class FakeHeaders:
    def __init__(self, content_type: str = "image/jpeg") -> None:
        self.content_type = content_type

    def get_content_type(self) -> str:
        return self.content_type


class FakeResponse:
    def __init__(self, payload: bytes, url: str, content_type: str = "image/jpeg") -> None:
        self.payload = payload
        self.url = url
        self.status = 200
        self.headers = FakeHeaders(content_type)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def geturl(self) -> str:
        return self.url

    def read(self, size: int = -1) -> bytes:
        if not self.payload:
            return b""
        if size is None or size < 0:
            chunk, self.payload = self.payload, b""
            return chunk
        chunk, self.payload = self.payload[:size], self.payload[size:]
        return chunk


def png_bytes(size=(120, 180)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, "teal").save(buffer, format="PNG")
    return buffer.getvalue()


def test_allowed_cover_hosts():
    assert lookup.is_allowed_cover_url("https://covers.openlibrary.org/b/id/1-L.jpg")
    assert lookup.is_allowed_cover_url("https://ia600507.us.archive.org/file.jpg")
    assert lookup.is_allowed_cover_url("http://books.google.com/books/content?id=1")
    assert lookup.is_allowed_cover_url(
        "https://m.media-amazon.com/images/S/compressed.photo.goodreads.com/books/1.jpg"
    )
    assert lookup.is_allowed_cover_url("https://i.gr-assets.com/images/S/compressed.photo.goodreads.com/books/1.jpg")
    assert not lookup.is_allowed_cover_url("https://evil.example/capa.jpg")
    assert not lookup.is_allowed_cover_url("https://covers.openlibrary.org.evil.example/x.jpg")
    assert not lookup.is_allowed_cover_url("https://covers.openlibrary.org:8080/x.jpg")
    assert not lookup.is_allowed_cover_url("http://127.0.0.1/cover.jpg")
    assert not lookup.is_allowed_cover_url("file:///etc/passwd")
    assert not lookup.is_allowed_cover_url(None)


def test_signed_cover_token_roundtrip(app):
    with app.app_context():
        url = "https://covers.openlibrary.org/b/id/123-L.jpg"
        token = lookup.sign_cover_url(url)
        assert lookup.verify_cover_token(token) == url
        assert lookup.verify_cover_token("token-invalido") is None
        assert lookup.verify_cover_token(token[:-2] + "xx") is None
        with pytest.raises(CoverLookupError):
            lookup.sign_cover_url("https://evil.example/capa.jpg")


def test_openlibrary_candidates_are_signed_and_ranked(app, monkeypatch):
    payload = {
        "docs": [
            {
                "title": "Outro livro",
                "author_name": ["Autora"],
                "cover_i": 1,
                "first_publish_year": 1999,
            },
            {
                "title": "Clean Code",
                "author_name": ["Robert C. Martin"],
                "cover_i": 8065615,
                "first_publish_year": 2008,
                "number_of_pages_median": 464,
            },
        ]
    }
    monkeypatch.setattr(lookup, "_fetch_json", lambda url: payload)

    with app.app_context():
        results = lookup._openlibrary_search("Clean Code Robert C. Martin")

    assert results[0]["title"] == "Clean Code"
    assert results[0]["preview"] == "https://covers.openlibrary.org/b/id/8065615-L.jpg"
    assert results[0]["source"] == "Open Library"
    assert results[0]["token"]
    assert "_score" not in results[0]


def test_google_jsonp_candidate(app, monkeypatch):
    payload = (
        'var _GBSBookInfo = {"ISBN:9780140328721": {"thumbnail_url": '
        '"https://books.google.com/books/content?id=DlQbmJc5WlQC&printsec=frontcover&img=1&zoom=5"}};'
    )
    monkeypatch.setattr(lookup, "_fetch_json", lambda url, allow_jsonp=False: {
        "ISBN:9780140328721": {
            "thumbnail_url": "https://books.google.com/books/content?id=DlQbmJc5WlQC&printsec=frontcover&img=1&zoom=5"
        }
    })
    with app.app_context():
        candidate = lookup._google_books_isbn("9780140328721", "Matilda", "Roald Dahl")
    assert candidate is not None
    assert "zoom=1" in candidate["preview"]
    assert candidate["source"] == "Google Books · ISBN"


def test_search_falls_back_and_rejects_no_candidates(app, monkeypatch):
    monkeypatch.setattr(lookup, "_openlibrary_search", lambda *args, **kwargs: [])
    monkeypatch.setattr(lookup, "_openlibrary_isbn_cover", lambda *args, **kwargs: None)
    monkeypatch.setattr(lookup, "_goodreads_isbn_cover", lambda *args, **kwargs: None)
    monkeypatch.setattr(lookup, "_google_books_isbn", lambda *args, **kwargs: None)
    with app.app_context():
        assert lookup.search_cover_candidates(isbn="9780000000000") == []


def test_search_raises_when_every_provider_fails(app, monkeypatch):
    def boom(*args, **kwargs):
        raise CoverLookupError("indisponível", "service_unavailable")

    monkeypatch.setattr(lookup, "_openlibrary_search", boom)
    monkeypatch.setattr(lookup, "_openlibrary_isbn_cover", boom)
    monkeypatch.setattr(lookup, "_goodreads_isbn_cover", boom)
    monkeypatch.setattr(lookup, "_google_books_isbn", boom)
    with app.app_context():
        with pytest.raises(CoverLookupError):
            lookup.search_cover_candidates(isbn="9780000000000")


def test_download_rejects_disallowed_host_before_network():
    with pytest.raises(CoverLookupError):
        lookup.download_cover("http://127.0.0.1/cover.jpg")
    with pytest.raises(CoverLookupError):
        lookup.download_cover("https://evil.example/cover.jpg")


def test_download_validates_redirect_and_content(app, monkeypatch):
    data = png_bytes()
    fake = FakeResponse(data, "https://ia600507.us.archive.org/cover.jpg")
    monkeypatch.setattr(lookup, "urlopen", lambda request, timeout=None: fake)
    with app.app_context():
        payload, content_type = lookup.download_cover(
            "https://covers.openlibrary.org/b/id/1-L.jpg"
        )
    assert payload == data
    assert content_type == "image/jpeg"

    fake_redirect = FakeResponse(data, "https://evil.example/cover.jpg")
    monkeypatch.setattr(lookup, "urlopen", lambda request, timeout=None: fake_redirect)
    with app.app_context():
        with pytest.raises(CoverLookupError):
            lookup.download_cover("https://covers.openlibrary.org/b/id/1-L.jpg")


def test_download_enforces_size_limit(app, monkeypatch):
    fake = FakeResponse(b"x" * 5000, "https://covers.openlibrary.org/cover.jpg")
    monkeypatch.setattr(lookup, "urlopen", lambda request, timeout=None: fake)
    app.config["COVER_LOOKUP_MAX_BYTES"] = 100
    with app.app_context():
        with pytest.raises(CoverLookupError):
            lookup.download_cover("https://covers.openlibrary.org/cover.jpg")


def test_save_cover_from_url_uses_pillow(app, monkeypatch, tmp_path):
    monkeypatch.setattr(lookup, "download_cover", lambda url: (png_bytes(), "image/png"))
    with app.app_context():
        filename = lookup.save_cover_from_url(
            "https://covers.openlibrary.org/cover.png", tmp_path
        )
    assert filename and filename.endswith(".jpg")
    saved = tmp_path / filename
    assert saved.exists()
    with Image.open(saved) as image:
        assert image.format == "JPEG"


def test_lookup_route_requires_login_and_input(client):
    anonymous = client.post("/books/cover-lookup", data={"title": "Clean Code"})
    assert anonymous.status_code == 302

    login = client.post(
        "/register",
        data={
            "name": "Bia",
            "email": "bia@example.com",
            "password": "abcd",
            "confirm": "abcd",
        },
        follow_redirects=True,
    )
    assert login.status_code == 200
    response = client.post("/books/cover-lookup", data={})
    assert response.status_code == 400
    assert response.get_json()["ok"] is False


def test_lookup_route_returns_candidates(auth_client, monkeypatch):
    candidates = [
        {
            "preview": "https://covers.openlibrary.org/b/id/1-L.jpg",
            "token": "signed-token",
            "title": "Clean Code",
            "authors": "Robert C. Martin",
            "source": "Open Library",
            "year": "2008",
            "pages": "464",
        }
    ]

    def fake_search(**kwargs):
        assert kwargs["title"] == "Clean Code"
        return candidates

    monkeypatch.setattr(routes, "search_cover_candidates", fake_search)
    response = auth_client.post(
        "/books/cover-lookup",
        data={"title": "Clean Code", "authors": "Robert C. Martin"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["candidates"] == candidates
    assert "1 capa" in payload["message"]


def test_lookup_route_handles_service_error(auth_client, monkeypatch):
    def boom(**kwargs):
        raise CoverLookupError("Serviço fora do ar.", "service_unavailable")

    monkeypatch.setattr(routes, "search_cover_candidates", boom)
    response = auth_client.post(
        "/books/cover-lookup", data={"isbn": "9780140328721"}
    )
    assert response.status_code == 502
    assert response.get_json()["message"] == "Serviço fora do ar."


def test_lookup_route_can_be_disabled(app, auth_client):
    app.config["COVER_LOOKUP_ENABLED"] = False
    response = auth_client.post("/books/cover-lookup", data={"title": "Clean Code"})
    assert response.status_code == 503


def test_book_save_uses_signed_cover_candidate(app, auth_client, monkeypatch, tmp_path):
    monkeypatch.setattr(
        routes,
        "verify_cover_token",
        lambda token: "https://covers.openlibrary.org/b/id/1-L.jpg",
    )

    def fake_save(url, folder):
        assert url.startswith("https://covers.openlibrary.org/")
        target = Path(folder) / "remote-cover.jpg"
        target.write_bytes(png_bytes())
        return target.name

    monkeypatch.setattr(routes, "save_cover_from_url", fake_save)
    create_book(
        auth_client,
        title="Livro com capa remota",
        cover_url="",
        cover_candidate="signed-token",
    )

    with app.app_context():
        from models import Book

        book = Book.query.filter_by(title="Livro com capa remota").one()
        assert book.cover_filename == "remote-cover.jpg"


def test_book_save_ignores_invalid_cover_token(app, auth_client, monkeypatch):
    monkeypatch.setattr(routes, "verify_cover_token", lambda token: None)
    response = create_book(
        auth_client,
        title="Capa expirada",
        cover_url="",
        cover_candidate="expirado",
    )
    assert response.status_code == 200
    assert "expirou" in response.get_data(as_text=True)
    with app.app_context():
        from models import Book

        assert Book.query.filter_by(title="Capa expirada").one().cover_filename is None


def test_book_save_survives_download_failure(app, auth_client, monkeypatch):
    monkeypatch.setattr(
        routes,
        "verify_cover_token",
        lambda token: "https://covers.openlibrary.org/b/id/1-L.jpg",
    )

    def fail(url, folder):
        raise CoverLookupError("Não foi possível baixar a capa.", "download_failed")

    monkeypatch.setattr(routes, "save_cover_from_url", fail)
    response = create_book(
        auth_client,
        title="Capa indisponível",
        cover_url="",
        cover_candidate="signed-token",
    )
    assert response.status_code == 200
    assert "Não foi possível baixar" in response.get_data(as_text=True)
    with app.app_context():
        from models import Book

        assert Book.query.filter_by(title="Capa indisponível").one().cover_filename is None


def test_goodreads_extracts_largest_cover_and_signs(app, monkeypatch):
    html = """
    <img src="https://m.media-amazon.com/images/S/compressed.photo.goodreads.com/books/1697126323i/199541067._SX150_.jpg"
         srcSet="https://m.media-amazon.com/images/S/compressed.photo.goodreads.com/books/1697126323i/199541067._SX300_.jpg 2x">
    <img src="https://m.media-amazon.com/images/S/compressed.photo.goodreads.com/books/1697126323i/199541067.jpg">
    """
    monkeypatch.setattr(lookup, "_fetch_goodreads_html", lambda url: html)
    with app.app_context():
        candidate = lookup._goodreads_isbn_cover(
            "9788535914849", "1984", "George Orwell"
        )
    assert candidate is not None
    assert candidate["preview"].endswith("199541067.jpg")
    assert candidate["source"] == "Goodreads · ISBN"
    assert candidate["token"]


def test_goodreads_search_page_without_cover_returns_none(app, monkeypatch):
    monkeypatch.setattr(
        lookup, "_fetch_goodreads_html", lambda url: "<html>sem capa aqui</html>"
    )
    with app.app_context():
        assert lookup._goodreads_isbn_cover("9780000000000", "Nada", "Ninguém") is None


def test_search_uses_goodreads_fallback_before_google(app, monkeypatch):
    monkeypatch.setattr(lookup, "_openlibrary_search", lambda *args, **kwargs: [])
    monkeypatch.setattr(lookup, "_openlibrary_isbn_cover", lambda *args, **kwargs: None)

    def fake_goodreads(isbn, title, authors):
        return lookup._candidate(
            "https://m.media-amazon.com/images/S/compressed.photo.goodreads.com/books/1.jpg",
            title=title,
            authors=authors,
            source="Goodreads · ISBN",
        )

    def fail_google(*args, **kwargs):
        raise AssertionError("Google Books não deveria ser consultado")

    monkeypatch.setattr(lookup, "_goodreads_isbn_cover", fake_goodreads)
    monkeypatch.setattr(lookup, "_google_books_isbn", fail_google)

    with app.app_context():
        results = lookup.search_cover_candidates(
            isbn="9788535914849", title="1984", authors="George Orwell"
        )
    assert len(results) == 1
    assert results[0]["source"] == "Goodreads · ISBN"
