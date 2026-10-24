"""Normalização de texto para busca sem acentos."""

from __future__ import annotations

import unicodedata


def strip_accents(value: str | None) -> str | None:
    """Remove acentos e normaliza caixa sem depender de extensões do banco."""
    if value is None:
        return None
    decomposed = unicodedata.normalize("NFKD", str(value))
    return "".join(
        character for character in decomposed if not unicodedata.combining(character)
    ).casefold()
