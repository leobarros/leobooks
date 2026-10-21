from __future__ import annotations

from models import User, db
from tests.helpers import extract_csrf, register


def test_register_creates_user_and_session(app, client):
    response = register(client, name="Carla", email="carla@example.com", password="abcd")
    assert response.status_code == 200
    assert b"caderno" in response.data.lower()
    with app.app_context():
        user = User.query.one()
        assert user.email == "carla@example.com"
        assert user.password_hash != "abcd"
        assert user.password_hash.startswith(("scrypt:", "pbkdf2:"))


def test_register_rejects_short_and_long_passwords(app, client):
    for password in ("abc", "12345678901"):
        response = client.post(
            "/register",
            data={
                "name": "Teste",
                "email": f"user{len(password)}@example.com",
                "password": password,
                "confirm": password,
            },
        )
        assert response.status_code == 200
        assert "entre 4 e 10 caracteres" in response.get_data(as_text=True)
    with app.app_context():
        assert User.query.count() == 0


def test_register_rejects_duplicate_email(app, client):
    register(client, email="dup@example.com")
    client.post("/logout")
    response = client.post(
        "/register",
        data={
            "name": "Outra",
            "email": "dup@example.com",
            "password": "abcd",
            "confirm": "abcd",
        },
    )
    assert "já está em uso" in response.get_data(as_text=True)


def test_login_and_logout(app, client):
    register(client, email="login@example.com", password="abcd")
    client.post("/logout", follow_redirects=True)
    response = client.post(
        "/login",
        data={"email": "login@example.com", "password": "abcd", "remember": "y"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Inicio" in response.data or "Início".encode() in response.data

    response = client.post("/logout", follow_redirects=True)
    assert "Sessão encerrada" in response.get_data(as_text=True)
    assert client.get("/").status_code == 302


def test_login_rejects_wrong_password(client):
    register(client, email="wrong@example.com", password="abcd")
    client.post("/logout")
    response = client.post(
        "/login",
        data={"email": "wrong@example.com", "password": "xxxx"},
        follow_redirects=True,
    )
    assert "incorretos" in response.get_data(as_text=True)


def test_open_redirect_is_blocked(client):
    register(client, email="redir@example.com", password="abcd")
    client.post("/logout")
    response = client.post(
        "/login?next=https://evil.example/steal",
        data={"email": "redir@example.com", "password": "abcd"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "evil.example" not in response.headers["Location"]
    assert response.headers["Location"].endswith("/")


def test_data_isolation_between_users(app, client):
    register(client, name="Dona", email="dona@example.com")
    client.post(
        "/books/new",
        data={
            "title": "Livro privado",
            "authors": "Autora",
            "total_pages": "100",
            "current_page": "10",
            "status": "READING",
        },
    )
    with app.app_context():
        from models import Book

        book_id = Book.query.one().id

    other = app.test_client()
    register(other, name="Intrusa", email="intrusa@example.com", password="zzzz")
    assert other.get(f"/books/{book_id}").status_code == 404
    assert other.get(f"/books/{book_id}/edit").status_code == 404
    assert other.get(f"/books/{book_id}/cover.svg").status_code == 404
    assert other.get("/library").status_code == 200


def test_csrf_is_enforced_and_csp_headers_are_set(csrf_app):
    client = csrf_app.test_client()
    blocked = client.post("/register", data={"name": "Sem token"})
    assert blocked.status_code == 400
    assert "Sessão expirada" in blocked.get_data(as_text=True)

    page = client.get("/register")
    token = extract_csrf(page.get_data(as_text=True))
    response = client.post(
        "/register",
        data={
            "csrf_token": token,
            "name": "Com token",
            "email": "csrf@example.com",
            "password": "abcd",
            "confirm": "abcd",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    csp = response.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "script-src 'self' 'nonce-" in csp
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"


def test_anonymous_redirected_to_login(client):
    response = client.get("/library")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
