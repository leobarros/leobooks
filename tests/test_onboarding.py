from __future__ import annotations

from tests.helpers import register
from models import Book, Note, User


def test_registration_creates_exactly_one_sample_book(app, client):
    app.config["SAMPLE_BOOK_ENABLED"] = True
    register(client, name="Nova Pessoa", email="nova@example.com", password="abcd")

    with app.app_context():
        user = User.query.filter_by(email="nova@example.com").one()
        assert user.onboarding_completed is False
        books = Book.query.filter_by(user_id=user.id).all()
        assert len(books) == 1
        book = books[0]
        assert book.title == "A Arte da Guerra"
        assert book.authors == "Sun Tzu"
        assert book.status == "WANT_TO_READ"
        assert Note.query.filter_by(book_id=book.id).count() == 0


def test_onboarding_tutorial_can_be_skipped_or_completed(app, auth_client):
    first_page = auth_client.get("/").get_data(as_text=True)
    assert 'id="onboardingModal"' in first_page
    assert "Pular tutorial" in first_page

    auth_client.post(
        "/settings/onboarding/complete",
        data={"next": "/library"},
        follow_redirects=True,
    )
    with app.app_context():
        assert User.query.filter_by(email="ana@example.com").one().onboarding_completed is True

    completed_page = auth_client.get("/").get_data(as_text=True)
    assert 'id="onboardingModal"' not in completed_page

    reset = auth_client.post("/settings/tutorial", follow_redirects=True)
    assert reset.status_code == 200
    with app.app_context():
        assert User.query.filter_by(email="ana@example.com").one().onboarding_completed is False
    assert 'id="onboardingModal"' in reset.get_data(as_text=True)


def test_sample_book_can_be_disabled(app, client):
    app.config["SAMPLE_BOOK_ENABLED"] = False
    register(client, name="Sem Exemplo", email="sem@example.com", password="abcd")
    with app.app_context():
        user = User.query.filter_by(email="sem@example.com").one()
        assert Book.query.filter_by(user_id=user.id).count() == 0
