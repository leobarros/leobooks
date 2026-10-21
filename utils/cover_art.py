"""Capas generativas em SVG.

Quando um livro não tem capa enviada nem URL externa, o LeoBooks desenha uma
capa editorial determinística a partir do título e do autor. O resultado é
leve, funciona offline e mantém a estante visualmente coesa.

O texto é escapado como XML antes de entrar no SVG.
"""

from __future__ import annotations

import hashlib
import textwrap
from xml.sax.saxutils import escape

# Cada paleta: fundo, tinta, acento e uma segunda cor de apoio.
PALETTES = [
    {"bg": "#173E33", "ink": "#F4EBD8", "accent": "#D9A441", "soft": "#2C5A4A"},
    {"bg": "#8E3F2C", "ink": "#F8EEDF", "accent": "#E7C27D", "soft": "#A8533C"},
    {"bg": "#C08A3E", "ink": "#251E15", "accent": "#F1E4C8", "soft": "#A9742C"},
    {"bg": "#223348", "ink": "#EFE6D2", "accent": "#C89B57", "soft": "#314963"},
    {"bg": "#4A2B3B", "ink": "#F2E7D5", "accent": "#C7A17A", "soft": "#5E3A4D"},
    {"bg": "#2F3B3A", "ink": "#EAE2D0", "accent": "#B9C7B0", "soft": "#425250"},
    {"bg": "#EADFC8", "ink": "#26211A", "accent": "#8E3F2C", "soft": "#DCCEB2"},
    {"bg": "#6F8871", "ink": "#F6EFDF", "accent": "#2B3D33", "soft": "#7E987F"},
    {"bg": "#B2573B", "ink": "#F7E9D6", "accent": "#EDC894", "soft": "#C26B4C"},
    {"bg": "#1D3B45", "ink": "#F1E7D3", "accent": "#D4925C", "soft": "#2A505C"},
]

MOTIFS = ("sun", "arch", "horizon", "orbit", "spine", "stairs")


def _digest(seed: str) -> int:
    return int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12], 16)


def _wrap(text: str, width: int, max_lines: int = 4) -> list[str]:
    words = (text or "Sem título").split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
        if len(lines) == max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if not lines:
        lines = ["Sem título"]
    if len(lines) == max_lines and words:
        # sinaliza truncamento de forma elegante
        last = lines[-1]
        if len(last) > width - 1:
            lines[-1] = last[: max(1, width - 1)].rstrip() + "…"
    return lines


def _motif(kind: str, palette: dict) -> str:
    accent = palette["accent"]
    soft = palette["soft"]
    if kind == "sun":
        return f"""
        <circle cx="452" cy="286" r="128" fill="{accent}" opacity="0.92"/>
        <circle cx="452" cy="286" r="180" fill="none" stroke="{accent}" stroke-width="1.4" opacity="0.5"/>
        <circle cx="452" cy="286" r="226" fill="none" stroke="{accent}" stroke-width="1" opacity="0.28"/>
        <path d="M120 286h664" stroke="{palette['ink']}" stroke-width="1" opacity="0.35"/>"""
    if kind == "arch":
        return f"""
        <path d="M150 640V420a150 150 0 0 1 300 0v220" fill="none" stroke="{accent}" stroke-width="3"/>
        <path d="M196 640V426a104 104 0 0 1 208 0v214" fill="{soft}" opacity="0.85"/>
        <path d="M242 640V432a58 58 0 0 1 116 0v208" fill="{palette['bg']}" stroke="{accent}" stroke-width="1.2"/>
        <circle cx="300" cy="470" r="7" fill="{accent}"/>
        <path d="M480 210h72v430" fill="none" stroke="{accent}" stroke-width="1.2" opacity="0.55"/>"""
    if kind == "horizon":
        return f"""
        <path d="M0 520c110-46 208-46 300 0s190 46 300 0" fill="none" stroke="{accent}" stroke-width="2.2"/>
        <path d="M0 556c110-46 208-46 300 0s190 46 300 0" fill="none" stroke="{accent}" stroke-width="1" opacity="0.5"/>
        <circle cx="430" cy="300" r="74" fill="{accent}" opacity="0.9"/>
        <path d="M0 520h600v180H0z" fill="{soft}" opacity="0.35"/>"""
    if kind == "orbit":
        return f"""
        <g transform="translate(300 330)">
          <circle r="150" fill="none" stroke="{accent}" stroke-width="1.4"/>
          <circle r="112" fill="none" stroke="{accent}" stroke-width="1" opacity="0.55"/>
          <circle r="64" fill="{soft}" opacity="0.9"/>
          <circle cx="150" cy="0" r="9" fill="{accent}"/>
          <circle cx="-80" cy="78" r="5" fill="{accent}" opacity="0.8"/>
          <path d="M-160 0h320" stroke="{palette['ink']}" stroke-width="0.8" opacity="0.3"/>
        </g>"""
    if kind == "spine":
        return f"""
        <rect x="70" y="170" width="46" height="420" fill="{accent}" opacity="0.9"/>
        <rect x="126" y="170" width="8" height="420" fill="{palette['ink']}" opacity="0.35"/>
        <g fill="none" stroke="{accent}" stroke-width="1.2" opacity="0.7">
          <path d="M210 590V260l90-60 90 60v330"/>
          <path d="M240 590V290l60-40 60 40v300"/>
          <path d="M270 590V318l30-20 30 20v272"/>
        </g>
        <circle cx="440" cy="240" r="52" fill="{accent}" opacity="0.75"/>"""
    return f"""
        <g fill="none" stroke="{accent}" stroke-width="1.6">
          <path d="M110 600h120V480h120V360h120V240"/>
          <path d="M110 640h160V520h160V400h160V280" opacity="0.4"/>
        </g>
        <circle cx="470" cy="240" r="14" fill="{accent}"/>"""


def cover_svg(title: str, authors: str = "", seed: str | None = None) -> str:
    """Retorna um SVG completo (600x900) para a capa do livro."""
    seed_value = seed or f"{title}|{authors}"
    value = _digest(seed_value)
    palette = PALETTES[value % len(PALETTES)]
    motif = MOTIFS[(value // 13) % len(MOTIFS)]

    safe_title = (title or "Sem título").strip()
    font_size = 50 if len(safe_title) <= 34 else 42
    width_chars = 17 if font_size == 50 else 21
    lines = _wrap(safe_title, width_chars, max_lines=4)

    line_height = 58 if font_size == 50 else 50
    block_height = len(lines) * line_height
    title_top = 742 - block_height
    if title_top < 470:
        title_top = 470

    title_spans = "\n".join(
        f'<tspan x="58" dy="{0 if index == 0 else line_height}">{escape(line)}</tspan>'
        for index, line in enumerate(lines)
    )

    safe_author = escape((authors or "").strip()[:52])
    ref = _digest(seed_value) % 900 + 100
    edition = f"{ref:04d}"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 900" role="img" aria-label="Capa de {escape(safe_title)}">
  <defs>
    <linearGradient id="shade" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#000" stop-opacity="0.16"/>
      <stop offset="0.22" stop-color="#000" stop-opacity="0"/>
      <stop offset="1" stop-color="#000" stop-opacity="0.2"/>
    </linearGradient>
    <pattern id="grain" width="90" height="90" patternUnits="userSpaceOnUse">
      <circle cx="8" cy="12" r="0.8" fill="{palette['ink']}" opacity="0.18"/>
      <circle cx="42" cy="38" r="0.6" fill="{palette['ink']}" opacity="0.12"/>
      <circle cx="72" cy="74" r="0.7" fill="{palette['ink']}" opacity="0.15"/>
    </pattern>
    <clipPath id="frame"><rect width="600" height="900" rx="4"/></clipPath>
  </defs>
  <g clip-path="url(#frame)">
    <rect width="600" height="900" fill="{palette['bg']}"/>
    <rect width="600" height="900" fill="url(#grain)"/>
    <g opacity="0.92">{_motif(motif, palette)}</g>
    <rect x="20" y="20" width="560" height="860" fill="none" stroke="{palette['ink']}" stroke-width="0.9" opacity="0.28"/>
    <text x="58" y="78" font-family="Inter, Helvetica, Arial, sans-serif" font-size="13" letter-spacing="4.5" fill="{palette['ink']}" opacity="0.85">LEOBOOKS</text>
    <text x="542" y="78" text-anchor="end" font-family="Inter, Helvetica, Arial, sans-serif" font-size="11" letter-spacing="2" fill="{palette['ink']}" opacity="0.55">EDIÇÃO {edition}</text>
    <path d="M58 100h484" stroke="{palette['ink']}" stroke-width="0.9" opacity="0.35"/>
    <text x="58" y="{title_top}" font-family="Fraunces, Georgia, 'Times New Roman', serif" font-size="{font_size}" font-weight="500" fill="{palette['ink']}">{title_spans}</text>
    <path d="M58 800h72" stroke="{palette['accent']}" stroke-width="2.4"/>
    <text x="58" y="836" font-family="Inter, Helvetica, Arial, sans-serif" font-size="16" letter-spacing="2.6" fill="{palette['ink']}" opacity="0.82">{safe_author.upper()}</text>
    <text x="542" y="836" text-anchor="end" font-family="Fraunces, Georgia, serif" font-size="14" font-style="italic" fill="{palette['accent']}" opacity="0.9">caderno de leitura</text>
    <rect width="600" height="900" fill="url(#shade)"/>
  </g>
</svg>"""
