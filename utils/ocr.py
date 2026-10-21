"""OCR opcional de fotos de páginas.

O recurso é deliberadamente opcional: se o binário ``tesseract`` e o pacote
``pytesseract`` existirem no homelab, a extração de texto funciona; caso
contrário a interface avisa e a foto continua podendo ser anexada à nota.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from werkzeug.datastructures import FileStorage

from utils.memory_guard import HEAVY_MEDIA_LOCK


def ocr_available() -> bool:
    if shutil.which("tesseract") is None:
        return False
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        return False
    return True


def extract_text(file_storage: FileStorage) -> tuple[str, str | None]:
    """Extrai texto da imagem.

    Retorna ``(texto, erro)``. Nunca levanta exceção para o chamador.
    """
    if not ocr_available():
        return "", "ocr_unavailable"

    if file_storage is None or not getattr(file_storage, "filename", ""):
        return "", "empty_file"

    suffix = Path(file_storage.filename or "foto.jpg").suffix or ".jpg"
    temp_path = None
    try:
        import pytesseract
        from PIL import Image, ImageOps

        file_storage.stream.seek(0)
        with HEAVY_MEDIA_LOCK:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(file_storage.stream.read())
                temp_path = tmp.name

            with Image.open(temp_path) as image:
                image = ImageOps.exif_transpose(image)
                if image.width < 900:
                    scale = 900 / image.width
                    image = image.resize(
                        (900, int(image.height * scale)), Image.Resampling.LANCZOS
                    )
                text = pytesseract.image_to_string(
                    image, lang="por+eng", config="--psm 6"
                )
        cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        return cleaned.strip(), None
    except Exception:  # noqa: BLE001 - OCR é melhor-esforço
        return "", "ocr_failed"
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)
