"""Auditoria estruturada do LeoBooks.

Cada ação relevante gera **uma linha JSON** em stdout (e, opcionalmente, em um
arquivo com rotação). O formato é pensado para ``docker logs``/Loki/journald:

    {"timestamp":"2026-10-21T19:20:00.123Z","severity":"info","action":"auth.login",...}

Nunca registre senhas, tokens CSRF, conteúdo de notas ou o corpo de uploads.
A função aplica uma lista de bloqueio como defesa extra.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import g, has_request_context, request, session

AUDIT_LOGGER_NAME = "leobooks.audit"
MAX_FIELD_LENGTH = 300

# Defesa extra: mesmo que alguém passe um destes campos por engano, ele não vai
# para o log. IDs, títulos, tipos e contagens são permitidos.
BLOCKED_FIELDS = {
    "content",
    "password",
    "current_password",
    "new_password",
    "confirm",
    "confirm_password",
    "password_hash",
    "csrf_token",
    "token",
    "secret",
    "secret_key",
    "session",
    "cookie",
    "authorization",
    "photo",
    "upload",
    "backup",
    "image_data",
    "text",
}

VALID_SEVERITIES = {"debug", "info", "warning", "error", "critical"}
VALID_OUTCOMES = {"success", "failure", "denied"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _safe_value(value):
    if isinstance(value, str):
        return value if len(value) <= MAX_FIELD_LENGTH else value[:MAX_FIELD_LENGTH] + "…"
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value][:20]
    if isinstance(value, dict):
        return {
            str(key): _safe_value(item)
            for key, item in list(value.items())[:20]
            if str(key).casefold() not in BLOCKED_FIELDS
        }
    return str(value)[:MAX_FIELD_LENGTH]


def audit(
    action: str,
    *,
    outcome: str = "success",
    severity: str = "info",
    user_id: str | None = None,
    user_email: str | None = None,
    **fields,
) -> None:
    """Registra um evento de auditoria com contexto da requisição."""
    severity = severity if severity in VALID_SEVERITIES else "info"
    outcome = outcome if outcome in VALID_OUTCOMES else "success"

    event: dict = {
        "timestamp": _now(),
        "severity": severity,
        "event": "audit",
        "app": "leobooks",
        "action": action,
        "outcome": outcome,
    }

    if has_request_context():
        event["request_id"] = getattr(g, "request_id", None)
        event["ip"] = request.remote_addr
        event["method"] = request.method
        event["path"] = request.path

        started = getattr(g, "request_started", None)
        if started is not None:
            event["duration_ms"] = round((time.perf_counter() - started) * 1000, 1)

        cached_user = getattr(g, "current_user", None)
        if user_id is None and cached_user is not None:
            user_id = cached_user.id
        if user_email is None and cached_user is not None:
            user_email = cached_user.email
        if user_id is None:
            user_id = session.get("user_id")

    if user_id:
        event["user_id"] = user_id
    if user_email:
        event["user"] = user_email

    for key, value in fields.items():
        key = str(key)
        if key.casefold() in BLOCKED_FIELDS or value is None:
            continue
        event[key] = _safe_value(value)

    logger = logging.getLogger(AUDIT_LOGGER_NAME)
    log_method = getattr(logger, severity, logger.info)
    log_method(
        json.dumps(event, ensure_ascii=False, default=str, separators=(",", ":"))
    )


def configure_audit_logging(app) -> None:
    """Configura o logger de auditoria para stdout e arquivo opcional."""
    level_name = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    logger = logging.getLogger(AUDIT_LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    # Recria handlers (idempotente em testes e múltiplos app factories).
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:  # noqa: BLE001 - handler já pode estar fechado
            pass

    stream = logging.StreamHandler(sys.stdout)
    stream.setLevel(level)
    stream.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(stream)

    log_path = str(app.config.get("AUDIT_LOG_PATH") or "").strip()
    if log_path:
        path = Path(log_path)
        if not path.is_absolute():
            path = Path(app.root_path) / path
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            path,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(file_handler)

    # Ajuda a ver warnings/errors da aplicação no mesmo nível configurado.
    app.logger.setLevel(level)
