# syntax=docker/dockerfile:1

FROM python:3.13-slim-bookworm

ARG APP_UID=1000
ARG APP_GID=1000
ARG INSTALL_OCR=false
ARG LEOBOOKS_VERSION=dev

LABEL org.opencontainers.image.title="LeoBooks" \
      org.opencontainers.image.description="Caderno de leitura em Flask: livros, notas, citações e progresso de leitura." \
      org.opencontainers.image.url="https://hub.docker.com/repository/docker/nickolback/leobooks" \
      org.opencontainers.image.version="${LEOBOOKS_VERSION}"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=America/Sao_Paulo \
    LEOBOOKS_HOST=0.0.0.0 \
    LEOBOOKS_PORT=5057 \
    MALLOC_ARENA_MAX=2

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid "${APP_GID}" leobooks \
    && useradd --uid "${APP_UID}" --gid leobooks --create-home \
       --shell /usr/sbin/nologin leobooks

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# OCR é opcional: aumenta a imagem, mas permite extrair texto das fotos.
RUN if [ "${INSTALL_OCR}" = "true" ]; then \
        apt-get update \
        && apt-get install -y --no-install-recommends \
            tesseract-ocr tesseract-ocr-por \
        && rm -rf /var/lib/apt/lists/* \
        && pip install --no-cache-dir pytesseract; \
    fi

COPY --chown=leobooks:leobooks . .

RUN mkdir -p /app/instance \
    && chown -R leobooks:leobooks /app/instance

USER leobooks

EXPOSE 5057

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5057/healthz', timeout=3)" || exit 1

CMD ["gunicorn", \
     "--bind", "0.0.0.0:5057", \
     "--workers", "1", \
     "--worker-class", "gthread", \
     "--threads", "4", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--max-requests", "2000", \
     "--max-requests-jitter", "100", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "wsgi:app"]
