"""Utilitários compartilhados: sessão, datas, tags, progresso e filtros Jinja."""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timedelta, timezone
from functools import wraps
from urllib.parse import urlparse

from flask import abort, flash, g, redirect, request, session, url_for

from models import TAG_COLORS, Book, Tag, User, db

MONTHS_PT = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]
MONTHS_SHORT_PT = [
    "jan", "fev", "mar", "abr", "mai", "jun",
    "jul", "ago", "set", "out", "nov", "dez",
]
WEEKDAYS_PT = [
    "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
    "sexta-feira", "sábado", "domingo",
]

TAG_NAME_RE = re.compile(r"^[^,;#]{1,40}$")

SAMPLE_BOOK = {
    "title": "A Arte da Guerra",
    "authors": "Sun Tzu",
    "publisher": "Exemplo",
    "total_pages": 128,
    "current_page": 0,
    "status": "WANT_TO_READ",
}


# ---------------------------------------------------------------------------
# Sessão / autenticação
# ---------------------------------------------------------------------------
def current_user() -> User | None:
    """Usuário autenticado da requisição, com cache em ``g``."""
    if "current_user" not in g:
        user_id = session.get("user_id")
        g.current_user = db.session.get(User, user_id) if user_id else None
        if user_id and g.current_user is None:
            session.clear()
    return g.current_user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            next_url = request.full_path if request.method == "GET" else None
            flash("Entre na sua conta para continuar.", "warning")
            return redirect(url_for("auth.login", next=next_url))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    """Restringe uma rota ao administrador do servidor (backup/restauração)."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user is None:
            return redirect(url_for("auth.login"))
        if not user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def safe_next_url(target: str | None) -> str | None:
    """Aceita apenas caminhos internos (evita open redirect)."""
    if not target:
        return None
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return None
    if not target.startswith("/") or target.startswith("//"):
        return None
    return target


def redirect_back(
    fallback_endpoint: str = "main.dashboard",
    fallback_kwargs: dict | None = None,
):
    """Volta para a página de origem (interna) ou para um destino conhecido."""
    target = request.form.get("next") or request.args.get("next")
    safe = safe_next_url(target)
    if safe:
        return redirect(safe)
    return redirect(url_for(fallback_endpoint, **(fallback_kwargs or {})))


def create_sample_book(user: User) -> Book:
    """Cria o livro de exemplo entregue a cada novo caderno.

    É um clássico em domínio público, sem notas e com capa gerada. O usuário
    pode excluí-lo normalmente quando quiser começar do zero.
    """
    book = Book(
        user_id=user.id,
        title=SAMPLE_BOOK["title"],
        authors=SAMPLE_BOOK["authors"],
        publisher=SAMPLE_BOOK["publisher"],
        total_pages=SAMPLE_BOOK["total_pages"],
        current_page=SAMPLE_BOOK["current_page"],
        status=SAMPLE_BOOK["status"],
    )
    db.session.add(book)
    return book


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------
def normalize_tag_name(raw: str) -> str:
    return re.sub(r"\s+", " ", (raw or "").strip().lstrip("#")).strip()


def parse_tag_names(raw: str | None) -> list[str]:
    """Converte "filosofia, #foco" em nomes limpos e únicos (sem repetição)."""
    if not raw:
        return []
    names: list[str] = []
    seen: set[str] = set()
    for chunk in re.split(r"[,;]", raw):
        name = normalize_tag_name(chunk)
        if not name or not TAG_NAME_RE.match(name):
            continue
        key = name.casefold()
        if key not in seen:
            seen.add(key)
            names.append(name)
    return names[:8]


def cleanup_orphan_tags(user_id: str) -> None:
    """Remove tags que ficaram sem nenhuma nota após edição/exclusão."""
    orphans = Tag.query.filter(Tag.user_id == user_id, ~Tag.notes.any()).all()
    if not orphans:
        return
    for tag in orphans:
        db.session.delete(tag)
    db.session.commit()


def tag_color(name: str) -> str:
    digest = hashlib.sha256(name.casefold().encode("utf-8")).hexdigest()
    return TAG_COLORS[int(digest[:8], 16) % len(TAG_COLORS)]


def resolve_tags(user: User, names: list[str]) -> list[Tag]:
    """Busca/cria tags do usuário preservando a grafia já existente.

    Considera também as tags ainda pendentes na sessão (antes do flush), para
    que várias notas criadas no mesmo pedido compartilhem a mesma tag.
    """
    existing = {
        tag.name.casefold(): tag for tag in Tag.query.filter_by(user_id=user.id).all()
    }
    for obj in db.session.new:
        if isinstance(obj, Tag) and obj.user_id == user.id:
            existing.setdefault(obj.name.casefold(), obj)

    resolved: list[Tag] = []
    for name in names:
        key = name.casefold()
        tag = existing.get(key)
        if tag is None:
            tag = Tag(
                user_id=user.id,
                name=name,
                color_hex=tag_color(name),
            )
            db.session.add(tag)
            existing[key] = tag
        resolved.append(tag)
    return resolved


# ---------------------------------------------------------------------------
# Datas
# ---------------------------------------------------------------------------
def _local(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone()
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    return None


def format_date_long(value: datetime | None) -> str:
    local = _local(value)
    if not local:
        return ""
    return f"{local.day} de {MONTHS_PT[local.month - 1]} de {local.year}"


def format_date_short(value: datetime | None) -> str:
    local = _local(value)
    if not local:
        return ""
    return f"{local.day:02d} {MONTHS_SHORT_PT[local.month - 1]} {local.year}"


def format_time(value: datetime | None) -> str:
    local = _local(value)
    return local.strftime("%H:%M") if local else ""


def weekday_long(value: date | datetime | None = None) -> str:
    reference = value or date.today()
    return WEEKDAYS_PT[reference.weekday()]


def time_ago(value: datetime | None) -> str:
    local = _local(value)
    if not local:
        return ""
    now = datetime.now(local.tzinfo)
    delta = now - local
    seconds = delta.total_seconds()

    if seconds < 60:
        return "agora mesmo"
    if seconds < 3600:
        minutes = int(seconds // 60)
        return f"há {minutes} min"
    if seconds < 86400:
        hours = max(1, int(seconds // 3600))
        return "há 1 hora" if hours == 1 else f"há {hours} horas"
    days = int(seconds // 86400)
    if days == 1:
        return "ontem"
    if days < 7:
        return f"há {days} dias"
    if days < 30:
        weeks = days // 7
        return "há 1 semana" if weeks == 1 else f"há {weeks} semanas"
    if days < 365:
        months = max(1, days // 30)
        return "há 1 mês" if months == 1 else f"há {months} meses"
    years = days // 365
    return "há 1 ano" if years == 1 else f"há {years} anos"


def greeting_for_now() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Bom dia"
    if hour < 18:
        return "Boa tarde"
    return "Boa noite"


# ---------------------------------------------------------------------------
# Métricas de leitura
# ---------------------------------------------------------------------------
def reading_streak_dates(dates) -> int:
    """Dias consecutivos (terminando hoje ou ontem) a partir de timestamps."""
    days = set()
    for value in dates:
        local = _local(value)
        if local:
            days.add(local.date())
    if not days:
        return 0

    today = date.today()
    cursor = today if today in days else today - timedelta(days=1)
    if cursor not in days:
        return 0

    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def reading_streak(notes) -> int:
    """Compatibilidade: calcula o streak a partir de objetos com created_at."""
    return reading_streak_dates([note.created_at for note in notes])


def week_activity_dates(dates) -> list[dict]:
    """Sete colunas (segunda → domingo) com a contagem de notas do dia."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    counts: dict[date, int] = {}
    for value in dates:
        local = _local(value)
        if local:
            counts[local.date()] = counts.get(local.date(), 0) + 1

    labels = ["S", "T", "Q", "Q", "S", "S", "D"]
    activity = []
    for index in range(7):
        day = monday + timedelta(days=index)
        activity.append(
            {
                "date": day,
                "label": labels[index],
                "count": counts.get(day, 0),
                "is_today": day == today,
                "is_future": day > today,
            }
        )
    return activity


def week_activity(notes) -> list[dict]:
    """Compatibilidade: calcula a semana a partir de objetos com created_at."""
    return week_activity_dates([note.created_at for note in notes])


def register_template_helpers(app) -> None:
    app.jinja_env.filters.update(
        {
            "data_longa": format_date_long,
            "data_curta": format_date_short,
            "hora": format_time,
            "tempo_atras": time_ago,
        }
    )
