from forms import BookForm, PTBRForm


def test_default_wtforms_messages_are_in_brazilian_portuguese(app):
    with app.test_request_context():
        form = BookForm(
            data={
                "title": "Livro",
                "authors": "Autora",
                "media_type": "PHYSICAL",
                "status": "",
            }
        )
        assert not form.validate()
        assert "Preencha este campo." in form.status.errors


def test_ptbr_translation_covers_length_and_number_defaults():
    assert PTBRForm._em_portugues("This field is required.") == "Preencha este campo."
    assert (
        PTBRForm._em_portugues("Field must be at most 255 characters long.")
        == "Use no máximo 255 caracteres."
    )
    assert (
        PTBRForm._em_portugues("Number must be between 0 and 100.")
        == "Informe um número entre 0 e 100."
    )


def test_sidebar_quotes_rotate_and_are_rendered(auth_client):
    from datetime import date

    from helpers import SIDEBAR_QUOTES, sidebar_quote

    assert len(SIDEBAR_QUOTES) >= 8
    first = sidebar_quote(date(2026, 1, 1))
    second = sidebar_quote(date(2026, 1, 2))
    assert first["author"] != second["author"] or first["text"] != second["text"]
    page = auth_client.get("/").get_data(as_text=True)
    current = sidebar_quote()
    assert current["text"] in page
    assert current["author"] in page
