"""Consulta opcional de definições no Wikcionário em português.

A API do Dicio não é pública; o Wikcionário oferece uma API MediaWiki aberta.
Só a palavra é enviada. O resultado é uma sugestão: o usuário pode editar a
definição antes de salvar no caderno local.
"""

from __future__ import annotations

import json
import re
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

API_URL = "https://pt.wiktionary.org/w/api.php"
SOURCE_NAME = "Wikcionário"
SOURCE_BASE = "https://pt.wiktionary.org/wiki/"
MAX_WORD = 80


class DictionaryError(RuntimeError):
    pass


class WordNotFound(DictionaryError):
    pass


def _clean_definition(extract: str) -> str:
    lines = []
    for raw in (extract or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("=") or line.startswith("__"):
            continue
        lines.append(line)
    text = "\n".join(lines).strip()
    # Evita despejar uma página inteira em uma nota; a API já vem em texto puro.
    if len(text) > 1800:
        text = text[:1797].rstrip() + "…"
    return text


def lookup_word(word: str) -> dict[str, str]:
    clean = re.sub(r"\s+", " ", (word or "").strip())
    if not clean or len(clean) > MAX_WORD:
        raise WordNotFound("Informe uma palavra válida.")

    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": "1",
        "titles": clean,
        "format": "json",
        "formatversion": "2",
        "redirects": "1",
    }
    request = Request(
        f"{API_URL}?{urlencode(params)}",
        headers={"User-Agent": "LeoBooks/1.0 (dicionário local; uso pessoal)"},
    )
    try:
        with urlopen(request, timeout=7) as response:
            payload = json.load(response)
    except Exception as exc:  # noqa: BLE001 - rede/JSON/HTTP viram falha de consulta
        raise DictionaryError("Não foi possível consultar o dicionário agora.") from exc

    pages = payload.get("query", {}).get("pages", [])
    if not pages:
        raise WordNotFound("Palavra não encontrada no Wikcionário.")
    page = pages[0]
    if page.get("missing") or not page.get("extract"):
        raise WordNotFound("Palavra não encontrada no Wikcionário.")

    definition = _clean_definition(page["extract"])
    if not definition:
        raise WordNotFound("O Wikcionário não trouxe uma definição legível.")

    return {
        "word": page.get("title") or clean,
        "definition": definition,
        "source": SOURCE_NAME,
        "source_url": f"{SOURCE_BASE}{quote(clean.replace(' ', '_'))}",
    }
