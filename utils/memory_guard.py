"""Serialização de operações pesadas de mídia.

Pillow/Tesseract alocam buffers grandes por operação. Com 4 threads, duas
operações simultâneas poderiam se aproximar do teto de 512 MB. Um único lock
compartilhado mantém o pico previsível sem bloquear requisições normais.
"""

from __future__ import annotations

import threading

HEAVY_MEDIA_LOCK = threading.Lock()
