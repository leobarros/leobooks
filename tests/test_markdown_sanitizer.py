from __future__ import annotations

from markupsafe import Markup

from utils.markdown_helper import excerpt, plain_text, render_markdown


def test_renders_basic_markdown():
    html = render_markdown("**forte** e *ênfase*\n\n- um\n- dois")
    assert isinstance(html, Markup)
    assert "<strong>forte</strong>" in html
    assert "<em>ênfase</em>" in html
    assert "<ul>" in html and "<li>um</li>" in html


def test_removes_script_tags():
    html = render_markdown("<script>alert('xss')</script>")
    assert "<script" not in html
    assert "alert" in html  # o texto permanece, a tag não


def test_removes_event_handlers_and_iframes():
    html = render_markdown(
        '<img src="x" onerror="alert(1)">\n\n<iframe src="https://evil.example"></iframe>'
    )
    assert "onerror" not in html
    assert "<iframe" not in html


def test_blocks_javascript_protocols():
    html = render_markdown("[clique](javascript:alert(1))")
    assert "javascript:" not in html.lower()


def test_keeps_safe_links_and_images():
    html = render_markdown('[site](https://example.com) ![capa](https://example.com/a.png)')
    assert 'href="https://example.com"' in html
    assert 'src="https://example.com/a.png"' in html
    assert 'rel=' not in html


def test_strips_style_and_form_tags():
    html = render_markdown('<style>body{display:none}</style><form action="/x"><input></form>')
    assert "<style" not in html
    assert "<form" not in html
    assert "<input" not in html


def test_plain_text_removes_markup():
    text = plain_text("# Título\n\n**Forte** e [link](https://example.com).")
    assert text == "Título Forte e link."
    assert "<" not in text


def test_excerpt_truncates_at_word_boundary():
    text = excerpt("palavra " * 60, length=40)
    assert len(text) <= 42
    assert text.endswith("…")


def test_empty_input_returns_empty_markup():
    assert str(render_markdown("")) == ""
    assert str(render_markdown(None)) == ""
    assert plain_text(None) == ""
