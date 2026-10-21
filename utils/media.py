"""Armazenamento seguro de imagens enviadas (capas e fotos de páginas).

As imagens nunca são gravadas em ``static/``: ficam em ``instance/`` e são
servidas por rotas autenticadas que verificam a propriedade do registro.
O Pillow reescreve o arquivo (removendo EXIF e metadados) e limita dimensões.
"""

from __future__ import annotations

import io
import uuid
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.datastructures import FileStorage

from config import Config
from utils.memory_guard import HEAVY_MEDIA_LOCK

Image.MAX_IMAGE_PIXELS = Config.MAX_IMAGE_PIXELS

ALLOWED_EXTENSIONS = Config.ALLOWED_IMAGE_EXTENSIONS



class MediaError(ValueError):
    """Erro de validação de uma imagem enviada."""


def _extension(filename: str | None) -> str:
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def save_image(
    file_storage: FileStorage | None,
    destination: Path,
    *,
    max_size: tuple[int, int] = (1600, 1600),
    quality: int = 84,
) -> str | None:
    """Valida, normaliza e grava a imagem; devolve o nome do arquivo final.

    Retorna ``None`` quando nenhum arquivo foi enviado.
    """
    if file_storage is None or not getattr(file_storage, "filename", ""):
        return None

    extension = _extension(file_storage.filename)
    if extension not in ALLOWED_EXTENSIONS:
        raise MediaError("Formato de imagem não suportado. Use JPG, PNG ou WebP.")

    destination.mkdir(parents=True, exist_ok=True)
    file_storage.stream.seek(0)

    with HEAVY_MEDIA_LOCK:
        try:
            with Image.open(file_storage.stream) as original:
                original.load()
                image = ImageOps.exif_transpose(original)
                if image.mode in ("RGBA", "LA", "P"):
                    background = Image.new("RGB", image.size, (255, 252, 245))
                    rgba = image.convert("RGBA")
                    background.paste(rgba, mask=rgba.getchannel("A"))
                    image = background
                else:
                    image = image.convert("RGB")
                image.thumbnail(max_size, Image.Resampling.LANCZOS)

                buffer = io.BytesIO()
                image.save(
                    buffer,
                    format="JPEG",
                    quality=quality,
                    optimize=True,
                    progressive=True,
                )
                buffer.seek(0)
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise MediaError("O arquivo enviado não é uma imagem válida.") from exc

        filename = f"{uuid.uuid4().hex}.jpg"
        (destination / filename).write_bytes(buffer.getvalue())
        return filename


def remove_image(destination: Path, filename: str | None) -> None:
    """Remove um arquivo de imagem, ignorando ausências (idempotente)."""
    if not filename:
        return
    # Impede qualquer tentativa de path traversal vindo do banco.
    safe_name = Path(filename).name
    target = destination / safe_name
    try:
        target.unlink(missing_ok=True)
    except OSError:  # pragma: no cover - permissões em homelab
        pass
