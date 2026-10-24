"""Backup completo do LeoBooks em um único arquivo ZIP.

O arquivo contém:

- ``leobooks.db``: snapshot consistente do SQLite;
- ``covers/``: capas armazenadas localmente;
- ``uploads/``: fotos das notas;
- ``manifest.json``: formato, contagens e checksums.

O banco é copiado com a API de backup do SQLite (sem copiar WAL/SHM no meio de
uma escrita). A restauração valida caminhos, tamanhos, checksums, integridade
do banco e referências a capas/fotos antes de substituir qualquer dado.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable

BACKUP_FORMAT = "leobooks-backup"
BACKUP_VERSION = 1
DB_ARCNAME = "leobooks.db"
MANIFEST_ARCNAME = "manifest.json"
ASSET_DIRS = ("covers", "uploads")
REQUIRED_TABLES = {"users", "books", "notes", "tags", "note_tags"}
DEFAULT_MAX_UNCOMPRESSED = 1024 * 1024 * 1024  # 1 GB


class BackupError(ValueError):
    """Arquivo de backup inválido ou inseguro."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _snapshot_database(source: Path, destination: Path) -> None:
    """Copia o SQLite de forma consistente, mesmo com WAL ativo."""
    source_conn = sqlite3.connect(source)
    dest_conn = sqlite3.connect(destination)
    try:
        with dest_conn:
            source_conn.backup(dest_conn)
    finally:
        source_conn.close()
        dest_conn.close()


def _counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("users", "books", "notes", "tags", "note_tags")
    }


def _iter_assets(directory: Path, prefix: str) -> Iterable[tuple[Path, str]]:
    if not directory.exists():
        return
    for path in sorted(directory.iterdir()):
        if path.is_file() and not path.is_symlink():
            yield path, f"{prefix}/{path.name}"


def _add_file(
    archive: zipfile.ZipFile,
    files: dict[str, dict],
    path: Path,
    arcname: str,
    *,
    compress_type: int,
) -> None:
    archive.write(path, arcname, compress_type=compress_type)
    files[arcname] = {
        "sha256": _sha256(path),
        "size": path.stat().st_size,
    }


def build_full_backup(
    *,
    db_path: Path,
    covers_dir: Path,
    uploads_dir: Path,
    destination: Path,
) -> dict:
    """Cria o ZIP completo e devolve o manifesto gerado."""
    db_path = Path(db_path)
    covers_dir = Path(covers_dir)
    uploads_dir = Path(uploads_dir)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    fd, snapshot_name = tempfile.mkstemp(
        prefix=".leobooks-snapshot-", suffix=".db", dir=destination.parent
    )
    snapshot = Path(snapshot_name)
    try:
        with open(fd, "wb"):
            pass
        _snapshot_database(db_path, snapshot)
        connection = sqlite3.connect(snapshot)
        try:
            counts = _counts(connection)
        finally:
            connection.close()

        files: dict[str, dict] = {}
        with zipfile.ZipFile(
            destination, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True
        ) as archive:
            _add_file(
                archive,
                files,
                snapshot,
                DB_ARCNAME,
                compress_type=zipfile.ZIP_DEFLATED,
            )
            for directory, prefix in ((covers_dir, "covers"), (uploads_dir, "uploads")):
                for asset, arcname in _iter_assets(directory, prefix):
                    _add_file(
                        archive,
                        files,
                        asset,
                        arcname,
                        compress_type=zipfile.ZIP_STORED,
                    )

            manifest = {
                "format": BACKUP_FORMAT,
                "version": BACKUP_VERSION,
                "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "database": DB_ARCNAME,
                "counts": counts,
                "files": files,
            }
            archive.writestr(
                MANIFEST_ARCNAME,
                json.dumps(manifest, ensure_ascii=False, indent=2),
                compress_type=zipfile.ZIP_DEFLATED,
            )
        return manifest
    finally:
        snapshot.unlink(missing_ok=True)


def validate_sqlite(path: Path) -> tuple[bool, str]:
    path = Path(path)
    try:
        with path.open("rb") as handle:
            if handle.read(16) != b"SQLite format 3\x00":
                return False, "O arquivo não é um banco SQLite válido."
        connection = sqlite3.connect(path)
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                return False, "O banco de dados está corrompido."
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            missing = REQUIRED_TABLES - tables
            if missing:
                return False, "O backup não parece ser do LeoBooks (tabelas ausentes)."
            users = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            if users < 1:
                return False, "O backup não contém nenhuma conta."
            foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
            if foreign_key_errors:
                return False, "O banco de backup tem referências inválidas."
        finally:
            connection.close()
    except (sqlite3.DatabaseError, OSError):
        return False, "Não foi possível ler o banco de backup."
    return True, ""


def _safe_archive_name(name: str) -> bool:
    if name in (DB_ARCNAME, MANIFEST_ARCNAME):
        return True
    if "\\" in name or "\x00" in name or name.startswith("/") or ".." in name:
        return False
    parts = PurePosixPath(name).parts
    if len(parts) != 2 or parts[0] not in ASSET_DIRS:
        return False
    filename = parts[1]
    return bool(filename) and filename not in {".", ".."} and PurePosixPath(filename).name == filename


def extract_and_validate(
    archive_path: Path,
    destination: Path,
    *,
    max_uncompressed_bytes: int = DEFAULT_MAX_UNCOMPRESSED,
) -> tuple[dict, Path, Path, Path]:
    """Extrai e valida o ZIP; devolve manifesto e caminhos dos dados."""
    archive_path = Path(archive_path)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    try:
        archive = zipfile.ZipFile(archive_path, "r")
    except (zipfile.BadZipFile, OSError) as exc:
        raise BackupError("O arquivo não é um ZIP de backup válido.") from exc

    with archive:
        entries = archive.infolist()
        names: set[str] = set()
        total = 0
        for info in entries:
            if info.is_dir():
                raise BackupError("O ZIP contém diretórios inesperados.")
            if info.flag_bits & 0x1:
                raise BackupError("O backup não pode conter arquivos criptografados.")
            name = info.filename
            if not _safe_archive_name(name):
                raise BackupError("O ZIP contém um caminho não permitido.")
            if name in names:
                raise BackupError("O ZIP contém arquivos duplicados.")
            if info.external_attr & 0o170000 == 0o120000:
                raise BackupError("O ZIP contém um link simbólico.")
            names.add(name)
            total += info.file_size
            if total > max_uncompressed_bytes:
                raise BackupError("O conteúdo do backup ultrapassa o limite permitido.")

        if DB_ARCNAME not in names or MANIFEST_ARCNAME not in names:
            raise BackupError("O ZIP não contém o banco e o manifesto do LeoBooks.")

        for info in entries:
            target = destination / info.filename
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("wb") as handle:
                shutil.copyfileobj(source, handle, length=1024 * 1024)

    try:
        manifest = json.loads((destination / MANIFEST_ARCNAME).read_text("utf-8"))
    except (OSError, ValueError) as exc:
        raise BackupError("O manifesto do backup é inválido.") from exc
    if manifest.get("format") != BACKUP_FORMAT or manifest.get("version") != BACKUP_VERSION:
        raise BackupError("Este backup foi gerado por uma versão incompatível.")
    declared = manifest.get("files")
    if not isinstance(declared, dict) or not declared:
        raise BackupError("O manifesto não contém a lista de arquivos.")

    actual = {
        info.filename: destination / info.filename
        for info in entries
        if info.filename != MANIFEST_ARCNAME
    }
    if set(actual) != set(declared):
        raise BackupError("O conteúdo do ZIP não corresponde ao manifesto.")
    for name, metadata in declared.items():
        path = actual.get(name)
        if path is None or not isinstance(metadata, dict):
            raise BackupError("O manifesto aponta para um arquivo ausente.")
        if path.stat().st_size != metadata.get("size"):
            raise BackupError("O tamanho de um arquivo do backup não confere.")
        if _sha256(path) != metadata.get("sha256"):
            raise BackupError("A verificação de integridade do backup falhou.")

    db_path = destination / DB_ARCNAME
    valid, message = validate_sqlite(db_path)
    if not valid:
        raise BackupError(message)

    # Garante que capas/fotos referenciadas no banco existam no ZIP.
    connection = sqlite3.connect(db_path)
    try:
        for table, column, prefix in (
            ("books", "cover_filename", "covers"),
            ("notes", "image_filename", "uploads"),
        ):
            rows = connection.execute(
                f"SELECT {column} FROM {table} WHERE {column} IS NOT NULL"
            ).fetchall()
            for (filename,) in rows:
                if not filename:
                    continue
                if PurePosixPath(str(filename)).name != str(filename):
                    raise BackupError("O banco contém um nome de arquivo inválido.")
                if not (destination / prefix / str(filename)).is_file():
                    raise BackupError(
                        "O backup não contém todas as capas ou fotos referenciadas."
                    )
    finally:
        connection.close()

    covers = destination / "covers"
    uploads = destination / "uploads"
    covers.mkdir(parents=True, exist_ok=True)
    uploads.mkdir(parents=True, exist_ok=True)
    return manifest, db_path, covers, uploads
