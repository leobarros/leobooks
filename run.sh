#!/usr/bin/env bash
# Sobe o LeoBooks com Waitress (WSGI) na porta 5057.
set -euo pipefail
cd "$(dirname "$0")"

HOST="${LEOBOOKS_HOST:-${HOST:-127.0.0.1}}"
PORT="${LEOBOOKS_PORT:-${PORT:-5057}}"

if [ ! -x ".venv/bin/waitress-serve" ]; then
  echo "Ambiente não encontrado. Rode: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

export MALLOC_ARENA_MAX="${MALLOC_ARENA_MAX:-2}"
exec .venv/bin/waitress-serve --listen="${HOST}:${PORT}" --threads=4 wsgi:app
