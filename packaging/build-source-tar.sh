#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${VERSION:-$(tr -d '[:space:]' < "$ROOT/VERSION")}"
mkdir -p "$ROOT/dist"
cd "$ROOT"
tar -czf "dist/leobooks-${VERSION}.tar.gz" \
  --transform="s,^,leobooks-${VERSION}/," \
  --exclude='__pycache__' --exclude='*.pyc' \
  app.py config.py models.py routes.py helpers.py forms.py wsgi.py \
  gunicorn.conf.py requirements.txt VERSION README.md \
  static templates utils packaging/common
echo "Gerado: $ROOT/dist/leobooks-${VERSION}.tar.gz"
