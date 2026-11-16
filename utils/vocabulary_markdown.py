"""Exportação e importação portátil do vocabulário em Markdown.

O formato é uma tabela legível, com um comentário de versão. Campos opcionais
são aceitos para permitir evolução do formato; o import ignora colunas que não
conhece.
"""

from __future__ import annotations

import re
from typing import Any

MARKER_RE = re.compile(r"<!--\s*leobooks-vocabulary:v(\d+)\s*-->", re.IGNORECASE)
HEADERS = ("Palavra", "Definição", "Contexto", "Livro", "Capítulo", "Página")


class VocabularyMarkdownError(ValueError):
    """Arquivo de vocabulário inválido ou incompatível."""


def _escape(value: Any) -> str:
    return str(value or "").replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def _unescape(value: str) -> str:
    return value.replace("\\|", "|").replace("\\\\", "\\")


def render_vocabulary_markdown(words) -> str:
    """Gera o Markdown de todas as palavras do usuário."""
    ordered = sorted(
        words,
        key=lambda word: (
            (word.book.title.casefold() if word.book else "~"),
            (word.chapter or "~").casefold(),
            word.page_number if word.page_number is not None else 100001,
            word.word.casefold(),
        ),
    )
    lines = [
        "# Vocabulário — LeoBooks",
        "",
        "<!-- leobooks-vocabulary:v1 -->",
        "_Arquivo portátil do vocabulário do LeoBooks. Importe em outro caderno "
        "ou guarde como cópia de leitura._",
        "",
        "| " + " | ".join(HEADERS) + " |",
        "| " + " | ".join("---" for _ in HEADERS) + " |",
    ]
    for word in ordered:
        lines.append(
            "| "
            + " | ".join(
                _escape(value)
                for value in (
                    word.word,
                    word.definition,
                    word.context,
                    word.book.title if word.book else "",
                    word.chapter,
                    word.page_number,
                )
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def _row_cells(line: str) -> list[str]:
    content = line.strip()
    if content.startswith("|"):
        content = content[1:]
    if content.endswith("|"):
        content = content[:-1]
    return [_unescape(cell.strip()) for cell in re.split(r"(?<!\\)\|", content)]


def parse_vocabulary_markdown(text: str) -> tuple[int, list[dict[str, Any]]]:
    """Lê o Markdown e devolve a versão e as palavras.

    A versão 1 é o formato atual. Versões futuras que mantenham os mesmos
    cabeçalhos continuam legíveis; colunas desconhecidas são ignoradas.
    """
    if not isinstance(text, str) or not text.strip():
        raise VocabularyMarkdownError("O arquivo de vocabulário está vazio.")

    marker = MARKER_RE.search(text)
    version = int(marker.group(1)) if marker else 1

    table_lines = [
        line for line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    if not table_lines:
        raise VocabularyMarkdownError(
            "Não encontrei a tabela de vocabulário no arquivo Markdown."
        )

    header = _row_cells(table_lines[0])
    normalized = [cell.casefold() for cell in header]
    required = {"palavra", "definição"}
    if not required <= set(normalized):
        raise VocabularyMarkdownError(
            "A tabela precisa ter as colunas Palavra e Definição."
        )
    positions = {name: index for index, name in enumerate(normalized)}

    entries: list[dict[str, Any]] = []
    for line in table_lines[1:]:
        cells = _row_cells(line)
        if not cells or all(set(cell) <= {"-", ":", " "} for cell in cells):
            continue

        def get(name: str) -> str:
            index = positions.get(name)
            return cells[index].strip() if index is not None and index < len(cells) else ""

        word = get("palavra")
        definition = get("definição")
        if not word or not definition:
            continue
        page_raw = get("página")
        page_number = int(page_raw) if page_raw.isdigit() else None
        entries.append(
            {
                "word": word,
                "definition": definition,
                "context": get("contexto") or None,
                "book": get("livro") or None,
                "chapter": get("capítulo") or None,
                "page_number": page_number,
            }
        )
    return version, entries
