from __future__ import annotations

from pathlib import Path

from tests.helpers import create_book, create_note


def test_anonymous_pages_render(client):
    assert client.get("/login").status_code == 200
    assert client.get("/register").status_code == 200
    assert client.get("/healthz").data == b"ok"
    assert client.get("/nao-existe").status_code == 404
    assert "Página fora da estante" in client.get("/nao-existe").get_data(as_text=True)


def test_authenticated_pages_render(auth_client, book):
    create_note(auth_client, book["id"], content="A **grande** ideia", tags="filosofia")

    checks = {
        "/": "Revisão diária",
        "/library": "Sua estante",
        "/tags": "fios",
        "/review": "Releia o que você",
        "/settings": "Dados e backup",
        "/books/new": "Coloque um livro",
        f"/books/{book['id']}": "O Poder do Hábito",
        "/search?q=grande": "A <strong>grande</strong> ideia",
    }
    for url, expected in checks.items():
        response = auth_client.get(url)
        assert response.status_code == 200, url
        assert expected in response.get_data(as_text=True), url

    dashboard = auth_client.get("/").get_data(as_text=True)
    assert "<script>" not in dashboard
    assert "lb-bottomnav" in dashboard
    assert "lb-sidebar" in dashboard


def test_tag_detail_filters_notes(app, auth_client, book):
    create_note(auth_client, book["id"], content="Nota de filosofia", tags="filosofia")

    page = auth_client.get("/tags").get_data(as_text=True)
    assert "filosofia" in page

    with app.app_context():
        from models import Tag

        tag_id = Tag.query.one().id

    detail = auth_client.get(f"/tags/{tag_id}").get_data(as_text=True)
    assert "Nota de filosofia" in detail
    assert 'class="lb-tagcloud__item is-active"' in detail


def test_search_page_without_query(auth_client):
    response = auth_client.get("/search")
    assert response.status_code == 200
    assert "Encontre o que ficou" in response.get_data(as_text=True)


def test_review_empty_state(auth_client):
    response = auth_client.get("/review")
    assert response.status_code == 200
    assert "Ainda não há citações" in response.get_data(as_text=True)


def test_static_vendor_assets_are_local(app):
    root = Path(app.root_path)
    expected = [
        "static/vendor/bootstrap/css/bootstrap.min.css",
        "static/vendor/bootstrap/js/bootstrap.bundle.min.js",
        "static/vendor/bootstrap-icons/bootstrap-icons.css",
        "static/vendor/bootstrap-icons/fonts/bootstrap-icons.woff2",
        "static/css/style.css",
        "static/js/app.js",
        "static/css/fonts.css",
    ]
    for relative in expected:
        path = root / relative
        assert path.exists(), relative
        assert path.stat().st_size > 100

    html = app.test_client().get("/login").get_data(as_text=True)
    assert "cdn.jsdelivr.net" not in html
    assert "cdnjs" not in html
    assert "/static/vendor/bootstrap/css/bootstrap.min.css" in html


def test_security_headers_present(app):
    app.config["ENABLE_CSP"] = True
    response = app.test_client().get("/login")
    assert "Content-Security-Policy" in response.headers
    assert "script-src 'self' 'nonce-" in response.headers["Content-Security-Policy"]
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "camera=(self)" in response.headers["Permissions-Policy"]
