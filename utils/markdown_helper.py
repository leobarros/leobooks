"""Conversão de Markdown para HTML com sanitização XSS obrigatória.

Fluxo de segurança:
``markdown`` gera o HTML a partir do texto do usuário → ``bleach.clean``
remove qualquer tag/atributo fora da whitelist → o resultado é devolvido como
``Markup`` (somente depois da limpeza) para o Jinja não escapar duas vezes.

Nunca marque conteúdo como seguro antes de passar por ``bleach.clean``.
"""

from __future__ import annotations

import re
from html import unescape

import bleach
import markdown
from markupsafe import Markup

# Whitelist restrita: apenas formatação de leitura. Sem <script>, <style>,
# <iframe>, <form>, <svg> ou qualquer atributo de evento.
ALLOWED_TAGS = [
    "p", "br", "hr", "strong", "b", "em", "i", "u", "s", "del", "mark",
    "blockquote", "pre", "code", "span",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "a",
    "img",
    "table", "thead", "tbody", "tfoot", "tr", "th", "td",
    "sup", "sub",
]

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title"],
    "img": ["src", "alt", "title"],
    "th": ["align"],
    "td": ["align"],
    "code": ["class"],
    "span": ["class"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

_MARKDOWN_EXTENSIONS = ["extra", "sane_lists", "nl2br", "admonition"]

_TAG_RE = re.compile(r"<[^>]+>")
_MULTIPLE_SPACES = re.compile(r"\s+")
_NEWLINES = re.compile(r"\n{3,}")


def render_markdown(source: str | None) -> Markup:
    """Converte Markdown em HTML seguro para renderização no template."""
    if not source:
        return Markup("")

    raw_html = markdown.markdown(
        source,
        extensions=_MARKDOWN_EXTENSIONS,
        output_format="html5",
    )
    clean_html = bleach.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
        strip_comments=True,
    )
    return Markup(clean_html)


def plain_text(source: str | None) -> str:
    """Remove a marcação para gerar resumos, buscas e cards de compartilhamento."""
    if not source:
        return ""
    html = markdown.markdown(source, extensions=["extra", "sane_lists"])
    text = bleach.clean(html, tags=[], strip=True)
    text = unescape(_TAG_RE.sub(" ", text))
    text = _MULTIPLE_SPACES.sub(" ", text)
    return text.strip()


def plain_text_multiline(source: str | None) -> str:
    """Como :func:`plain_text`, mas preserva quebras de linha (pré-visualização)."""
    text = plain_text(source)
    return _NEWLINES.sub("\n\n", text)


def excerpt(source: str | None, length: int = 180) -> str:
    text = plain_text(source)
    if len(text) <= length:
        return text
    cut = text[: length + 1]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,.;:") + "…"
