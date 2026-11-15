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
            "book_id": book["id"],
        },
        follow_redirects=True,
    )
    assert created.status_code == 200
    assert "virtù" in created.get_data(as_text=True)

    with app.app_context():
        entry = VocabularyWord.query.one()
        assert entry.book_id == book["id"]
        assert entry.definition.startswith("Força")

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
