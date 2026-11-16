#!/usr/bin/env bash
# Sobe o LeoBooks com Waitress (WSGI) na porta 5057.
set -euo pipefail
cd "$(dirname "$0")"

HOST="${LEOBOOKS_HOST:-${HOST:-127.0.0.1}}"
PORT="${LEOBOOKS_PORT:-${PORT:-5057}}"

if [ -f assets/ascii-logo.txt ]; then
  cat assets/ascii-logo.txt
  printf '\n'
fi

if [ ! -x ".venv/bin/waitress-serve" ]; then
  echo "Ambiente não encontrado. Rode: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

export MALLOC_ARENA_MAX="${MALLOC_ARENA_MAX:-2}"
VERSION="$(tr -d '[:space:]' < VERSION 2>/dev/null || echo dev)"
BASE_URL="http://${HOST}:${PORT}"
echo "LeoBooks ${VERSION} · ambiente local"
echo "  escuta   ${BASE_URL}"
echo "  health   ${BASE_URL}/healthz"
echo "  status   ${BASE_URL}/status"
echo "  banco    ${LEOBOOKS_DATABASE:-${LEOBOOKS_INSTANCE:-instance}/leobooks.db}"
echo "  logs     startup + acesso JSON em stdout"
echo ""
exec .venv/bin/waitress-serve --listen="${HOST}:${PORT}" --threads=4 wsgi:app
