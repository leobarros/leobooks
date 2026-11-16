from __future__ import annotations

import json

from models import VocabularyWord, db


def test_vocabulary_create_search_and_delete(app, auth_client, book):
    page = auth_client.get("/vocabulary")
    assert page.status_code == 200
    assert "Palavras que" in page.get_data(as_text=True)

    created = auth_client.post(
        "/vocabulary",
        data={
            "word": "virtù",
            "definition": "Força que se conquista com a própria ação.",
            "context": "O Príncipe, capítulo VI.",
            "chapter": "VI",
            "page_number": "42",
            "book_id": book["id"],
        },
        follow_redirects=True,
    )
    assert created.status_code == 200
    assert "virtù" in created.get_data(as_text=True)
    assert "Cap. VI · pág. 42" in created.get_data(as_text=True)

    with app.app_context():
        entry = VocabularyWord.query.one()
        assert entry.book_id == book["id"]
        assert entry.definition.startswith("Força")
        assert entry.chapter == "VI"
        assert entry.page_number == 42

    searched = auth_client.get("/vocabulary?q=virtu").get_data(as_text=True)
    assert "virtù" in searched
    assert "O Príncipe" in searched

    duplicate = auth_client.post(
        "/vocabulary",
        data={
            "word": "VIRTÙ",
            "definition": "Outra definição.",
            "book_id": "",
        },
        follow_redirects=True,
    )
    assert "já está no seu vocabulário" in duplicate.get_data(as_text=True)
    with app.app_context():
        assert VocabularyWord.query.count() == 1

    with app.app_context():
        word_id = VocabularyWord.query.one().id
    removed = auth_client.post(
        f"/vocabulary/{word_id}/delete", follow_redirects=True
    )
    assert removed.status_code == 200
    with app.app_context():
        assert VocabularyWord.query.count() == 0


def test_vocabulary_lookup_returns_definition(auth_client, monkeypatch):
    import routes

    monkeypatch.setattr(
        routes.dictionary,
        "lookup_word",
        lambda word: {
            "word": "casa",
            "definition": "construção que serve de moradia",
            "source": "Wikcionário",
            "source_url": "https://pt.wiktionary.org/wiki/casa",
        },
    )
    response = auth_client.get("/vocabulary/lookup?word=casa")
    assert response.status_code == 200
    data = json.loads(response.get_data(as_text=True))
    assert data["ok"] is True
    assert data["definition"] == "construção que serve de moradia"
    assert data["source"] == "Wikcionário"


def test_vocabulary_lookup_handles_not_found(auth_client, monkeypatch):
    import routes

    def missing(_word):
        raise routes.dictionary.WordNotFound("Palavra não encontrada.")

    monkeypatch.setattr(routes.dictionary, "lookup_word", missing)
    response = auth_client.get("/vocabulary/lookup?word=xyzzz")
    assert response.status_code == 404
    data = json.loads(response.get_data(as_text=True))
    assert data["ok"] is False


def test_dictionary_parser_reads_mediawiki_extract(monkeypatch):
    from utils import dictionary

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(
                {
                    "query": {
                        "pages": [
                            {
                                "title": "casa",
                                "extract": "= Português =\n\nconstrução que serve de moradia\n",
                            }
                        ]
                    }
                }
            ).encode()

    monkeypatch.setattr(dictionary, "urlopen", lambda request, timeout: FakeResponse())
    result = dictionary.lookup_word("casa")
    assert result["definition"] == "construção que serve de moradia"
    assert result["source"] == "Wikcionário"


def test_dictionary_parser_handles_missing_page(monkeypatch):
    from utils import dictionary

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"query": {"pages": [{"missing": True}]}}).encode()

    monkeypatch.setattr(dictionary, "urlopen", lambda request, timeout: FakeResponse())
    try:
        dictionary.lookup_word("xyzzz")
    except dictionary.WordNotFound:
        pass
    else:
        raise AssertionError("palavra ausente deveria levantar WordNotFound")


def test_vocabulary_is_filtered_by_book_and_linked_from_book(app, auth_client, book):
    from tests.helpers import create_book

    create_book(auth_client, title="Outro Livro", isbn="9780000000002")
    with app.app_context():
        from models import Book

        other_book = Book.query.filter_by(title="Outro Livro").one()
        other_id = other_book.id

    for word, book_id in (("primeira", book["id"]), ("outra", other_id)):
        auth_client.post(
            "/vocabulary",
            data={
                "word": word,
                "definition": f"Definição de {word}.",
                "book_id": book_id,
            },
        )

    filtered = auth_client.get(f"/vocabulary?book_id={book['id']}")
    html = filtered.get_data(as_text=True)
    assert "Definição de primeira" in html
    assert "Definição de outra" not in html
    assert book["title"] in html

    detail = auth_client.get(f"/books/{book['id']}").get_data(as_text=True)
    assert f"/books/{book['id']}?tab=vocabulary" in detail


def test_vocabulary_migration_adds_location_columns(app):
    from sqlalchemy import inspect, text

    from app import _ensure_vocabulary_columns

    with app.app_context():
        db.session.execute(text("DROP TABLE vocabulary_words"))
        db.session.execute(
            text(
                "CREATE TABLE vocabulary_words ("
                "id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, "
                "book_id VARCHAR(36), word VARCHAR(80) NOT NULL, "
                "word_key VARCHAR(100) NOT NULL, definition TEXT, context TEXT, "
                "created_at DATETIME, updated_at DATETIME)"
            )
        )
        db.session.commit()
        _ensure_vocabulary_columns()
        columns = {
            column["name"]
            for column in inspect(db.engine).get_columns("vocabulary_words")
        }
        assert {"chapter", "page_number"} <= columns


def test_status_endpoint_reports_service_health(client):
    response = client.get("/status")
    assert response.status_code == 200
    data = response.get_json()
    assert data["service"] == "leobooks"
    assert data["status"] == "ok"
    assert data["checks"]["database"]["status"] == "ok"
    assert data["version"]
    assert data["environment"]
    assert data["uptime_seconds"] >= 0


def test_waitress_queue_filter_suppresses_routine_depth():
    import logging

    from utils.observability import QueueDepthFilter

    queue_filter = QueueDepthFilter()
    routine = logging.LogRecord(
        "waitress.queue", logging.WARNING, "", 0, "Task queue depth is 2", (), None
    )
    deep = logging.LogRecord(
        "waitress.queue", logging.WARNING, "", 0, "Task queue depth is 12", (), None
    )
    assert not queue_filter.filter(routine)
    assert queue_filter.filter(deep)


def test_http_request_emits_structured_access_event(client, monkeypatch):
    import app as app_module

    events = []
    monkeypatch.setattr(
        app_module,
        "audit",
        lambda action, **fields: events.append((action, fields)),
    )
    response = client.get("/login")
    assert response.status_code == 200
    access = [fields for action, fields in events if action == "http.request"]
    assert access
    assert access[-1]["status"] == 200
    assert access[-1]["endpoint"] == "auth.login"
    assert access[-1]["outcome"] == "success"


def test_startup_art_has_brand_and_author():
    from utils.observability import startup_art

    art = startup_art()
    assert "LeoBooks" in art
    assert "Criado por Leo Sales" in art
    assert "▄" in art


def test_vocabulary_edit_updates_meaning_and_location(app, auth_client, book):
    auth_client.post(
        "/vocabulary",
        data={
            "word": "virtude",
            "definition": "Definição antiga.",
            "book_id": book["id"],
        },
    )
    with app.app_context():
        entry = VocabularyWord.query.one()
        word_id = entry.id

    page = auth_client.get(f"/vocabulary/{word_id}/edit")
    assert page.status_code == 200
    assert "Definição antiga." in page.get_data(as_text=True)

    updated = auth_client.post(
        f"/vocabulary/{word_id}/edit",
        data={
            "definition": "Definição revisada e mais clara.",
            "context": "A palavra apareceu no capítulo novo.",
            "chapter": "4",
            "page_number": "77",
            "book_id": book["id"],
        },
        follow_redirects=True,
    )
    html = updated.get_data(as_text=True)
    assert updated.status_code == 200
    assert "Definição revisada e mais clara." in html
    assert "Cap. 4 · pág. 77" in html
    with app.app_context():
        entry = VocabularyWord.query.one()
        assert entry.definition == "Definição revisada e mais clara."
        assert entry.chapter == "4"
        assert entry.page_number == 77


def test_book_vocabulary_page_groups_by_chapter(app, auth_client, book):
    for word, chapter, page in (
        ("virtude", "XXI", "74"),
        ("fortuna", "XXI", "75"),
        ("ardil", "XVIII", "63"),
    ):
        auth_client.post(
            "/vocabulary",
            data={
                "word": word,
                "definition": f"Definição de {word}.",
                "book_id": book["id"],
                "chapter": chapter,
                "page_number": page,
            },
        )

    legacy = auth_client.get(
        f"/books/{book['id']}/vocabulary", follow_redirects=False
    )
    assert legacy.status_code == 302
    assert "tab=vocabulary" in legacy.headers["Location"]

    page = auth_client.get(f"/books/{book['id']}?tab=vocabulary")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "XXI" in html
    assert "XVIII" in html
    assert "virtude" in html
    assert "fortuna" in html
    assert "ardil" in html
    assert "3 palavras" in html
    assert "2 capítulos" in html


def test_vocabulary_markdown_export_and_import(app, auth_client, book):
    from io import BytesIO

    auth_client.post(
        "/vocabulary",
        data={
            "word": "virtude",
            "definition": "Definição original.",
            "book_id": book["id"],
            "chapter": "2",
            "page_number": "20",
        },
    )
    exported = auth_client.get("/vocabulary/export.md")
    assert exported.status_code == 200
    text = exported.get_data(as_text=True)
    assert "leobooks-vocabulary:v1" in text
    assert "| Palavra | Definição | Contexto | Livro | Capítulo | Página |" in text
    assert "virtude" in text
    assert book["title"] in text
    assert "attachment" in exported.headers["Content-Disposition"]

    markdown = f"""# Vocabulário — LeoBooks

<!-- leobooks-vocabulary:v1 -->

| Palavra | Definição | Contexto | Livro | Capítulo | Página |
| --- | --- | --- | --- | --- | --- |
| virtude | Definição duplicada. |  | {book['title']} | 2 | 20 |
| fortuna | O que não está sob controle humano. | O acaso. | {book['title']} | 3 | 30 |
| exílio | Afastamento da própria terra. |  | Livro Futuro | 1 | 9 |
"""
    imported = auth_client.post(
        "/vocabulary/import",
        data={"file": (BytesIO(markdown.encode()), "vocabulario.md")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert imported.status_code == 200
    html = imported.get_data(as_text=True)
    assert "Importação concluída: 2 nova(s)" in html
    assert "1 já existente" in html
    assert "1 sem livro correspondente" in html
    with app.app_context():
        words = {word.word: word for word in VocabularyWord.query.all()}
        assert set(words) == {"virtude", "fortuna", "exílio"}
        assert words["virtude"].definition == "Definição original."
        assert words["fortuna"].book_id == book["id"]
        assert words["exílio"].book_id is None
