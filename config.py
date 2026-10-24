"""Configuração central do LeoBooks.

Os valores podem ser sobrescritos por variáveis de ambiente, pensando na
implantação em homelab. Nenhum segredo fica versionado: quando ``SECRET_KEY``
não é informada, uma chave aleatória é criada em ``instance/.secret_key`` com
permissão restrita (0600).
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
# Instalações nativas usam /var/lib/leobooks; Docker e execução local mantêm
# o comportamento anterior em <projeto>/instance.
INSTANCE_DIR = Path(
    os.environ.get("LEOBOOKS_INSTANCE", str(BASE_DIR / "instance"))
).expanduser()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "sim"}


def _secret_key() -> str:
    env_value = os.environ.get("SECRET_KEY", "").strip()
    if env_value:
        return env_value

    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    key_file = INSTANCE_DIR / ".secret_key"
    if key_file.exists():
        stored = key_file.read_text(encoding="utf-8").strip()
        if stored:
            return stored

    generated = secrets.token_hex(32)
    key_file.write_text(generated, encoding="utf-8")
    try:
        key_file.chmod(0o600)
    except OSError:  # pragma: no cover - sistemas de arquivos sem POSIX
        pass
    return generated


class Config:
    # --- Núcleo -----------------------------------------------------------
    SECRET_KEY = _secret_key()
    DEBUG = _env_bool("LEOBOOKS_DEBUG", False)

    # Porta fora das faixas de serviços conhecidos de DevOps/SRE
    # (5000, 8000, 3000 e 8081 são explicitamente evitadas).
    HOST = os.environ.get("LEOBOOKS_HOST") or os.environ.get("HOST") or "127.0.0.1"
    PORT = int(os.environ.get("LEOBOOKS_PORT") or os.environ.get("PORT") or "5057")

    # Diretório de dados usado pelo app (Docker usa instance/; pacotes usam
    # /var/lib/leobooks via LEOBOOKS_INSTANCE).
    DATA_DIR = INSTANCE_DIR

    # --- Banco de dados ----------------------------------------------------
    DATABASE_PATH = Path(
        os.environ.get("LEOBOOKS_DATABASE", str(INSTANCE_DIR / "leobooks.db"))
    )
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{DATABASE_PATH}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_size": 2,
        "max_overflow": 2,
        "pool_timeout": 15,
        "pool_recycle": 1800,
        "connect_args": {"timeout": 20},
    }

    # --- Sessão e CSRF -----------------------------------------------------
    SESSION_COOKIE_NAME = "leobooks_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_bool("LEOBOOKS_HTTPS", False)
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 30  # 30 dias com "lembrar"

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 60 * 60 * 12
    WTF_CSRF_SSL_STRICT = _env_bool("LEOBOOKS_HTTPS", False)

    # --- Uploads -----------------------------------------------------------
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB; menos pico de memória no upload
    # Assets locais (CSS, JS, fontes, ícones) podem ser reutilizados pelo WebKit.
    SEND_FILE_MAX_AGE_DEFAULT = 3600
    UPLOAD_FOLDER = Path(
        os.environ.get("LEOBOOKS_UPLOADS", str(INSTANCE_DIR / "uploads"))
    )
    COVER_FOLDER = Path(
        os.environ.get("LEOBOOKS_COVERS", str(INSTANCE_DIR / "covers"))
    )
    BACKUP_FOLDER = Path(
        os.environ.get("LEOBOOKS_BACKUPS", str(INSTANCE_DIR / "backups"))
    )
    # O restore aceita um ZIP completo; o limite global de 8 MB continua valendo
    # para os demais uploads. O request de restore recebe este limite próprio.
    BACKUP_MAX_BYTES = int(
        os.environ.get("LEOBOOKS_BACKUP_MAX_BYTES", str(512 * 1024 * 1024))
    )
    BACKUP_MAX_UNCOMPRESSED_BYTES = int(
        os.environ.get("LEOBOOKS_BACKUP_MAX_UNCOMPRESSED", str(1024 * 1024 * 1024))
    )
    ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
    MAX_IMAGE_PIXELS = 16_000_000  # ~64 MB decodificada; evita bombas de imagem

    # --- E-mail / conta ----------------------------------------------------
    PASSWORD_MIN_LENGTH = 4
    PASSWORD_MAX_LENGTH = 10

    # --- Busca de capas em APIs públicas ----------------------------------
    COVER_LOOKUP_ENABLED = _env_bool("LEOBOOKS_COVER_LOOKUP", True)
    COVER_LOOKUP_TIMEOUT = float(os.environ.get("LEOBOOKS_LOOKUP_TIMEOUT", "8"))
    COVER_LOOKUP_MAX_BYTES = int(
        os.environ.get("LEOBOOKS_LOOKUP_MAX_BYTES", str(4 * 1024 * 1024))
    )

    # --- Logs e auditoria --------------------------------------------------
    LOG_LEVEL = os.environ.get("LEOBOOKS_LOG_LEVEL", "INFO").strip().upper()
    AUDIT_LOG_PATH = os.environ.get("LEOBOOKS_AUDIT_LOG", "").strip()

    # --- Primeiro acesso ---------------------------------------------------
    SAMPLE_BOOK_ENABLED = _env_bool("LEOBOOKS_SAMPLE_BOOK", True)

    # --- Aparência ---------------------------------------------------------
    DEFAULT_THEME = "light"

    # --- Cabeçalhos de segurança ------------------------------------------
    ENABLE_CSP = _env_bool("LEOBOOKS_CSP", True)


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SERVER_NAME = "localhost"
