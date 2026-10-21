from __future__ import annotations

from models import User, db
from tests.helpers import register


def new_user_payload(**overrides):
    data = {
        "name": "Clara Leitora",
        "email": "clara@example.com",
        "password": "abcd",
        "confirm": "abcd",
        "is_admin": "",
    }
    data.update(overrides)
    return data


def test_admin_can_open_user_management(auth_client):
    response = auth_client.get("/settings/users")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Criar usuário" in html
    assert "com acesso" in html
    assert "ana@example.com" in html


def test_admin_creates_user_who_can_log_in(app, auth_client):
    response = auth_client.post(
        "/settings/users", data=new_user_payload(), follow_redirects=True
    )
    assert response.status_code == 200
    assert "Usuário" in response.get_data(as_text=True)
    assert "criado" in response.get_data(as_text=True)

    with app.app_context():
        created = User.query.filter_by(email="clara@example.com").one()
        assert created.name == "Clara Leitora"
        assert created.is_admin is False
        assert created.theme == "light"
        assert created.password_hash != "abcd"

    login = app.test_client()
    logged = login.post(
        "/login",
        data={"email": "clara@example.com", "password": "abcd"},
        follow_redirects=True,
    )
    assert logged.status_code == 200
    assert "Clara" in logged.get_data(as_text=True)
    assert login.get("/settings/users").status_code == 403


def test_admin_can_create_another_admin(app, auth_client):
    auth_client.post(
        "/settings/users",
        data=new_user_payload(email="chefe@example.com", is_admin="y"),
        follow_redirects=True,
    )
    with app.app_context():
        created = User.query.filter_by(email="chefe@example.com").one()
        assert created.is_admin is True


def test_admin_rejects_duplicate_email(app, auth_client):
    response = auth_client.post(
        "/settings/users",
        data=new_user_payload(email="ana@example.com"),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Já existe uma conta" in response.get_data(as_text=True)
    with app.app_context():
        assert User.query.filter_by(email="ana@example.com").count() == 1


def test_admin_rejects_invalid_password(app, auth_client):
    too_short = auth_client.post(
        "/settings/users",
        data=new_user_payload(password="abc", confirm="abc"),
        follow_redirects=True,
    )
    assert "entre 4 e 10 caracteres" in too_short.get_data(as_text=True)

    mismatch = auth_client.post(
        "/settings/users",
        data=new_user_payload(password="abcd", confirm="efgh"),
        follow_redirects=True,
    )
    assert "não conferem" in mismatch.get_data(as_text=True)

    with app.app_context():
        assert User.query.filter_by(email="clara@example.com").count() == 0


def test_non_admin_cannot_manage_users(app, auth_client):
    other = app.test_client()
    register(other, name="Comum", email="comum@example.com", password="zzzz")

    assert other.get("/settings/users").status_code == 403
    response = other.post(
        "/settings/users",
        data=new_user_payload(email="invasora@example.com"),
    )
    assert response.status_code == 403
    with app.app_context():
        assert User.query.filter_by(email="invasora@example.com").count() == 0


def test_admin_link_is_visible_only_for_admin(auth_client, app):
    admin_html = auth_client.get("/settings").get_data(as_text=True)
    assert "/settings/users" in admin_html

    other = app.test_client()
    register(other, name="Comum", email="comum2@example.com", password="zzzz")
    common_html = other.get("/settings").get_data(as_text=True)
    assert "/settings/users" not in common_html
