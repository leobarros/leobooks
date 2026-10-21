"""Ponto de entrada WSGI para Gunicorn/Waitress.

    waitress-serve --listen=127.0.0.1:5057 wsgi:app
    gunicorn -w 2 -b 127.0.0.1:5057 wsgi:app
"""

from app import app, log_app_start

log_app_start()

__all__ = ["app"]
