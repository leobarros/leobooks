"""Busca de capas em bases públicas (Open Library, Goodreads e Google Books).

Princípios de segurança:
- as APIs consultadas são fixas; nenhuma URL fornecida pelo cliente é buscada;
- cada capa candidata é assinada (itsdangerous) e a URL é validada contra uma
  allowlist antes de qualquer download;
- o download segue redirecionamentos, mas valida o host final, o tipo de
  conteúdo e o tamanho máximo;
- a imagem passa por :func:`utils.media.save_image` (Pillow), que a reescreve,
  limita dimensões e remove metadados.

As APIs públicas recebem apenas ISBN/título/autor digitados no formulário.
"""

from __future__ import annotations

import html as html_lib
import json
import re
import unicodedata
from http.cookiejar import CookieJar
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, quote_plus, urlencode, urlparse, urlunparse
from urllib.request import (
    HTTPCookieProcessor,
    Request,
    build_opener,
    urlopen,
)

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.datastructures import FileStorage

from utils.media import MediaError, save_image

USER_AGENT = "LeoBooks/1.0 (caderno de leitura pessoal)"
MAX_JSON_BYTES = 2_000_000
MAX_HTML_BYTES = 2_500_000
DEFAULT_TIMEOUT = 8.0
DEFAULT_MAX_COVER_BYTES = 4 * 1024 * 1024

# Apenas hosts de capas conhecidos. Redirecionamentos do Open Library vão para
# subdomínios de archive.org; imagens do Google Books para books.google.com.
ALLOWED_COVER_HOSTS = {
    "covers.openlibrary.org",
    "books.google.com",
    "books.googleusercontent.com",
    "lh3.googleusercontent.com",
    "m.media-amazon.com",
    "images-na.ssl-images-amazon.com",
    "i.gr-assets.com",
    "s.gr-assets.com",
    "images.gr-assets.com",
}
GOODREADS_HOSTS = {"goodreads.com", "www.goodreads.com"}
ALLOWED_COVER_SUFFIXES = (".archive.org",)

COVER_TOKEN_SALT = "leobooks-cover-candidate"
COVER_TOKEN_MAX_AGE = 60 * 60 * 2


class CoverLookupError(RuntimeError):
    """Falha amigável na consulta/download de capas."""

    def __init__(self, message: str, code: str = "lookup_failed") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


# ---------------------------------------------------------------------------
# Validação de URLs
# ---------------------------------------------------------------------------
def is_allowed_cover_url(url: str | None) -> bool:
    """Aceita somente HTTP(S) em hosts de capas conhecidos, sem portas exóticas."""
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    try:
        if parsed.port not in (None, 80, 443):
            return False
    except ValueError:
        return False

    host = parsed.hostname.lower().rstrip(".")
    if host in ALLOWED_COVER_HOSTS:
        return True
    return any(host.endswith(suffix) for suffix in ALLOWED_COVER_SUFFIXES)


def _https(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme == "http":
        parsed = parsed._replace(scheme="https")
    return urlunparse(parsed)


# ---------------------------------------------------------------------------
# Token assinado (candidato -> URL de download)
# ---------------------------------------------------------------------------
def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"], salt=COVER_TOKEN_SALT
    )


def sign_cover_url(url: str) -> str:
    if not is_allowed_cover_url(url):
        raise CoverLookupError("Origem de capa não permitida.", "invalid_source")
    return _serializer().dumps({"u": _https(url)})


def verify_cover_token(token: str | None, max_age: int = COVER_TOKEN_MAX_AGE) -> str | None:
    if not token:
        return None
    try:
        payload = _serializer().loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(payload, dict):
        return None
    url = payload.get("u")
    return url if isinstance(url, str) and is_allowed_cover_url(url) else None


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def _timeout() -> float:
    try:
        return float(current_app.config.get("COVER_LOOKUP_TIMEOUT", DEFAULT_TIMEOUT))
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT


def _max_cover_bytes() -> int:
    try:
        return int(
            current_app.config.get("COVER_LOOKUP_MAX_BYTES", DEFAULT_MAX_COVER_BYTES)
        )
    except (TypeError, ValueError):
        return DEFAULT_MAX_COVER_BYTES


def _fetch_json(url: str, *, allow_jsonp: bool = False) -> dict:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/javascript,*/*;q=0.5",
        },
    )
    try:
        with urlopen(request, timeout=_timeout()) as response:
            raw = response.read(MAX_JSON_BYTES + 1)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise CoverLookupError(
            "Não foi possível consultar as bases de capas agora.",
            "service_unavailable",
        ) from exc

    if len(raw) > MAX_JSON_BYTES:
        raise CoverLookupError("Resposta grande demais da base de capas.", "invalid_response")

    text = raw.decode("utf-8", errors="replace").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        if not allow_jsonp:
            raise CoverLookupError(
                "A base de capas retornou uma resposta inesperada.", "invalid_response"
            )
        # Endpoint legado do Google: "var _GBSBookInfo = {...};"
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise CoverLookupError(
                "A base de capas retornou uma resposta inesperada.", "invalid_response"
            )
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise CoverLookupError(
                "A base de capas retornou uma resposta inesperada.", "invalid_response"
            ) from exc

    if not isinstance(data, dict):
        raise CoverLookupError("A base de capas retornou uma resposta inesperada.", "invalid_response")
    return data


def _image_available(url: str) -> bool:
    """Confirma que a URL devolve uma imagem (sem baixar o arquivo inteiro)."""
    if not is_allowed_cover_url(url):
        return False
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "image/*",
            "Range": "bytes=0-1024",
        },
    )
    try:
        with urlopen(request, timeout=_timeout()) as response:
            final_url = response.geturl()
            content_type = response.headers.get_content_type()
            status = getattr(response, "status", 200)
            return (
                status in (200, 206)
                and is_allowed_cover_url(final_url)
                and content_type.startswith("image/")
            )
    except (HTTPError, URLError, TimeoutError, OSError):
        return False


# ---------------------------------------------------------------------------
# Normalização e candidatos
# ---------------------------------------------------------------------------
def _clean_text(value: str | None, limit: int = 160) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


def _normalize_isbn(value: str | None) -> str:
    return re.sub(r"[^0-9Xx]", "", str(value or ""))[:20]


def _tokens(value: str | None) -> set[str]:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return {word for word in re.findall(r"[a-z0-9]+", ascii_text) if len(word) > 2}


def _title_score(candidate: str, wanted: str) -> float:
    wanted_tokens = _tokens(wanted)
    if not wanted_tokens:
        return 0.0
    candidate_tokens = _tokens(candidate)
    overlap = len(wanted_tokens & candidate_tokens) / len(wanted_tokens)
    # Bônus para o título contido literalmente no resultado.
    if _tokens(wanted) <= _tokens(candidate):
        overlap += 0.35
    return overlap


def _candidate(
    url: str,
    *,
    title: str = "",
    authors: str = "",
    source: str,
    year: str = "",
    pages: str = "",
) -> dict | None:
    url = _https(url)
    if not is_allowed_cover_url(url):
        return None
    return {
        "preview": url,
        "token": sign_cover_url(url),
        "title": _clean_text(title, 120),
        "authors": _clean_text(authors, 120),
        "source": source,
        "year": _clean_text(year, 12),
        "pages": _clean_text(pages, 12),
    }


# ---------------------------------------------------------------------------
# Open Library
# ---------------------------------------------------------------------------
def _author_score(candidate: str, wanted: str) -> float:
    wanted_tokens = _tokens(wanted)
    if not wanted_tokens:
        return 0.0
    candidate_tokens = _tokens(candidate)
    return len(wanted_tokens & candidate_tokens) / len(wanted_tokens)


def _openlibrary_search(
    query: str,
    *,
    title: str = "",
    authors: str = "",
    isbn: str = "",
    limit: int = 8,
) -> list[dict]:
    params = {
        "q": query,
        "limit": str(limit),
        "fields": "title,author_name,cover_i,isbn,first_publish_year,number_of_pages_median",
    }
    data = _fetch_json(f"https://openlibrary.org/search.json?{urlencode(params)}")
    docs = data.get("docs") or []
    if not isinstance(docs, list):
        return []

    candidates = []
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        cover_id = doc.get("cover_i")
        if not cover_id:
            continue
        try:
            cover_id = int(cover_id)
        except (TypeError, ValueError):
            continue
        doc_title = _clean_text(doc.get("title"), 120)
        doc_authors = ", ".join(
            _clean_text(author, 80)
            for author in (doc.get("author_name") or [])
            if isinstance(author, str)
        )[:160]
        year = doc.get("first_publish_year") or ""
        pages = doc.get("number_of_pages_median") or ""
        # Relevância: título + autor (para edições traduzidas) + ISBN exato.
        relevance = _title_score(doc_title, title or query)
        relevance += _author_score(doc_authors, authors) * 0.8
        if isbn:
            doc_isbns = {
                _normalize_isbn(value)
                for value in (doc.get("isbn") or [])
                if isinstance(value, str)
            }
            if isbn in doc_isbns:
                relevance += 1.5

        # Quando a busca é por título, descarta resultados claramente alheios.
        if title and relevance < 0.3:
            continue

        candidate = _candidate(
            f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg",
            title=doc_title,
            authors=doc_authors,
            source="Open Library",
            year=str(year),
            pages=str(pages),
        )
        if candidate:
            candidate["_score"] = relevance
            candidates.append(candidate)

    for candidate in candidates:
        candidate["_score"] = float(candidate.get("_score", 0.0))
    candidates.sort(key=lambda item: item["_score"], reverse=True)
    for candidate in candidates:
        candidate.pop("_score", None)
    return candidates[:limit]


def _openlibrary_isbn_cover(isbn: str, title: str, authors: str) -> dict | None:
    if not isbn:
        return None
    url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false"
    if not _image_available(url):
        return None
    return _candidate(url, title=title, authors=authors, source="Open Library · ISBN")


# ---------------------------------------------------------------------------
# Goodreads (fallback para catálogos com pouca cobertura no Open Library)
# ---------------------------------------------------------------------------
def _is_goodreads_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and parsed.hostname.lower().rstrip(".") in GOODREADS_HOSTS
    )


def _fetch_goodreads_html(url: str) -> str:
    """Busca HTML do Goodreads com cookie jar (o site redireciona sem cookies)."""
    jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Upgrade-Insecure-Requests": "1",
        },
    )
    try:
        with opener.open(request, timeout=_timeout()) as response:
            final_url = response.geturl()
            if not _is_goodreads_url(final_url):
                raise CoverLookupError(
                    "A busca de capa saiu do catálogo esperado.", "invalid_redirect"
                )
            raw = response.read(MAX_HTML_BYTES + 1)
    except CoverLookupError:
        raise
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise CoverLookupError(
            "Não foi possível consultar o Goodreads agora.", "service_unavailable"
        ) from exc

    if len(raw) > MAX_HTML_BYTES:
        raise CoverLookupError("Página de capas grande demais.", "invalid_response")
    return raw.decode("utf-8", errors="replace")


def _goodreads_isbn_cover(isbn: str, title: str, authors: str) -> dict | None:
    """Extrai a capa do primeiro resultado de uma busca por ISBN no Goodreads."""
    if not isbn:
        return None
    html = _fetch_goodreads_html(
        f"https://www.goodreads.com/search?q={quote_plus(isbn)}"
    )

    # Página de livro (redirect) ou resultado de busca: ambas expõem imagens
    # em /compressed.photo.goodreads.com/books/<id>i/<id>.jpg.
    covers = re.findall(
        r'https?://(?:m\.media-amazon\.com|i\.gr-assets\.com|'
        r'images-na\.ssl-images-amazon\.com)/[^"\s]*?/books/[^"\s]+?\.jpg',
        html,
        flags=re.IGNORECASE,
    )
    covers = [html_lib.unescape(url).replace("&amp;", "&") for url in covers]
    if not covers:
        return None

    # Prefere a imagem original (sem sufixo de redimensionamento) e, se não
    # existir, a maior variante _SX<n>_ disponível.
    originals = [url for url in covers if not re.search(r"\._SX\d+_\.jpg", url)]
    if originals:
        chosen = originals[0]
    else:
        def _size(url: str) -> int:
            match = re.search(r"\._SX(\d+)_\.jpg", url)
            return int(match.group(1)) if match else 0

        chosen = max(covers, key=_size)

    # Evita capas genéricas de "sem imagem".
    if "no-cover" in chosen.lower():
        return None
    return _candidate(
        chosen,
        title=title,
        authors=authors,
        source="Goodreads · ISBN",
    )


# ---------------------------------------------------------------------------
# Google Books (endpoint legado por ISBN)
# ---------------------------------------------------------------------------
def _upgrade_google_thumbnail(url: str) -> str:
    parsed = urlparse(_https(url))
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["zoom"] = "1"  # 128x~198; a imagem é reencodada ao salvar
    query["img"] = "1"
    if "printsec" not in query:
        query["printsec"] = "frontcover"
    return urlunparse(parsed._replace(query=urlencode(query)))


def _google_books_isbn(isbn: str, title: str, authors: str) -> dict | None:
    if not isbn:
        return None
    url = "https://books.google.com/books?jscmd=viewapi&bibkeys=" + urlencode(
        {"bibkeys": f"ISBN:{isbn}"}
    )
    data = _fetch_json(url, allow_jsonp=True)
    item = data.get(f"ISBN:{isbn}")
    if not isinstance(item, dict):
        # O endpoint pode devolver a chave em outra caixa/forma.
        item = next(
            (value for value in data.values() if isinstance(value, dict)),
            None,
        )
    if not isinstance(item, dict):
        return None
    thumbnail = item.get("thumbnail_url")
    if not isinstance(thumbnail, str):
        return None
    return _candidate(
        _upgrade_google_thumbnail(thumbnail),
        title=title,
        authors=authors,
        source="Google Books · ISBN",
    )


# ---------------------------------------------------------------------------
# API pública do módulo
# ---------------------------------------------------------------------------
def search_cover_candidates(
    isbn: str = "",
    title: str = "",
    authors: str = "",
    limit: int = 6,
) -> list[dict]:
    isbn = _normalize_isbn(isbn)
    title = _clean_text(title, 200)
    authors = _clean_text(authors, 200)
    if not isbn and not title:
        return []

    candidates: list[dict] = []
    attempts = 0
    errors = 0

    # 1) Busca textual na Open Library (boa cobertura e capas em alta resolução)
    if title:
        attempts += 1
        try:
            candidates.extend(
                _openlibrary_search(
                    " ".join(part for part in (title, authors) if part),
                    title=title,
                    authors=authors,
                    isbn=isbn,
                )
            )
        except CoverLookupError:
            errors += 1

    # 2) Capa direta por ISBN, quando ainda não há resultado textual
    if isbn and not candidates:
        attempts += 1
        try:
            direct = _openlibrary_isbn_cover(isbn, title, authors)
            if direct:
                candidates.append(direct)
        except CoverLookupError:
            errors += 1

    # 3) Goodreads por ISBN — cobre muitos lançamentos brasileiros que não
    # aparecem no Open Library.
    if isbn and not candidates:
        attempts += 1
        try:
            goodreads = _goodreads_isbn_cover(isbn, title, authors)
            if goodreads:
                candidates.append(goodreads)
        except CoverLookupError:
            errors += 1

    # 4) Google Books por ISBN como último recurso
    if isbn and not candidates:
        attempts += 1
        try:
            google = _google_books_isbn(isbn, title, authors)
            if google:
                candidates.append(google)
        except CoverLookupError:
            errors += 1

    # 5) Se só há ISBN e nada foi encontrado, tenta a busca textual pelo ISBN
    if isbn and not candidates:
        attempts += 1
        try:
            candidates.extend(_openlibrary_search(isbn, isbn=isbn, limit=4))
        except CoverLookupError:
            errors += 1

    unique: list[dict] = []
    seen: set[str] = set()
    for candidate in candidates:
        url = candidate.get("preview")
        if not url or url in seen:
            continue
        seen.add(url)
        unique.append(candidate)

    if not unique and attempts and errors == attempts:
        raise CoverLookupError(
            "As bases públicas não responderam. Tente novamente em alguns instantes.",
            "service_unavailable",
        )
    return unique[:limit]


# ---------------------------------------------------------------------------
# Download e gravação
# ---------------------------------------------------------------------------
def download_cover(url: str) -> tuple[bytes, str]:
    if not is_allowed_cover_url(url):
        raise CoverLookupError("Origem de capa não permitida.", "invalid_source")

    request = Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "image/*"},
    )
    max_bytes = _max_cover_bytes()
    try:
        with urlopen(request, timeout=_timeout()) as response:
            final_url = response.geturl()
            if not is_allowed_cover_url(final_url):
                raise CoverLookupError(
                    "A capa redirecionou para uma origem não permitida.",
                    "invalid_redirect",
                )
            content_type = response.headers.get_content_type()
            if not content_type.startswith("image/"):
                raise CoverLookupError("O endereço não devolveu uma imagem.", "invalid_type")

            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise CoverLookupError("A imagem da capa é grande demais.", "too_large")
                chunks.append(chunk)
            data = b"".join(chunks)
    except CoverLookupError:
        raise
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise CoverLookupError(
            "Não foi possível baixar a capa escolhida.", "download_failed"
        ) from exc

    if not data:
        raise CoverLookupError("A capa baixada está vazia.", "empty_image")
    return data, content_type


def save_cover_from_url(url: str, destination: Path) -> str:
    data, content_type = download_cover(url)
    suffix = ".png" if "png" in content_type else ".jpg"
    file_storage = FileStorage(
        stream=BytesIO(data),
        filename=f"cover{suffix}",
        content_type=content_type,
    )
    try:
        filename = save_image(
            file_storage,
            Path(destination),
            max_size=(1200, 1800),
        )
    except MediaError as exc:
        raise CoverLookupError(
            "A imagem baixada não pôde ser processada.", "invalid_image"
        ) from exc
    if not filename:
        raise CoverLookupError("A imagem da capa não pôde ser salva.", "save_failed")
    return filename
