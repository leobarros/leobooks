"""Utilitários compartilhados pelos testes funcionais."""

from __future__ import annotations

import re


def register(client, name="Bia", email="bia@example.com", password="abcd"):
    return client.post(
        "/register",
        data={"name": name, "email": email, "password": password, "confirm": password},
        follow_redirects=True,
    )


def create_book(client, **overrides):
    data = {
        "title": "O Poder do Hábito",
        "authors": "Charles Duhigg",
        "publisher": "Objetiva",
        "isbn": "9788539002545",
        "total_pages": "408",
        "current_page": "0",
        "status": "READING",
    }
    data.update(overrides)
    return client.post("/books/new", data=data, follow_redirects=True)


def create_note(client, book_id, content="Uma nota.", note_type="QUOTE", **extra):
    data = {
        "book_id": book_id,
        "type": note_type,
        "content": content,
        "chapter": extra.get("chapter", "2"),
        "page_number": extra.get("page_number", "42"),
        "tags": extra.get("tags", "atenção, método"),
    }
    return client.post("/notes/new", data=data, follow_redirects=True)


def extract_csrf(html: str) -> str:
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    if not match:
        match = re.search(r'value="([^"]+)"[^>]*name="csrf_token"', html)
    assert match, "csrf token não encontrado"
    return match.group(1)
