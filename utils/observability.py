"""Observabilidade operacional: versão, ambiente e ruído de servidor."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

VERSION_FILE = Path(__file__).resolve().parent.parent / "VERSION"
ART_FILE = Path(__file__).resolve().parent.parent / "assets" / "ascii-logo.txt"
QUEUE_WARNING = re.compile(r"^Task queue depth is (\d+)$")
QUEUE_ALERT_DEPTH = 10


def app_version() -> str:
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip() or "dev"
    except OSError:
        return "dev"


def startup_art() -> str:
    try:
        return ART_FILE.read_text(encoding="utf-8").rstrip()
    except OSError:
        return "LeoBooks"


def environment_name() -> str:
    explicit = (os.environ.get("LEOBOOKS_ENV") or "").strip().lower()
    if explicit:
        return explicit
    return "container" if Path("/.dockerenv").exists() else "local"


class QueueDepthFilter(logging.Filter):
    """Silencia o aviso normal do Waitress; preserva filas realmente profundas."""

    def filter(self, record: logging.LogRecord) -> bool:
        match = QUEUE_WARNING.match(record.getMessage())
        if not match:
            return True
        try:
            return int(match.group(1)) >= QUEUE_ALERT_DEPTH
        except ValueError:
            return True


def configure_server_logging() -> None:
    """Instala o filtro antes de o Waitress emitir seus avisos de fila."""
    logger = logging.getLogger("waitress.queue")
    if not any(isinstance(item, QueueDepthFilter) for item in logger.filters):
        logger.addFilter(QueueDepthFilter())
