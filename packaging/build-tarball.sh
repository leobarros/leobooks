#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${VERSION:-$(tr -d '[:space:]' < "$ROOT/VERSION")}"
STAGE="$ROOT/build/tarball/leobooks-${VERSION}"
OUT="$ROOT/dist/leobooks-${VERSION}-linux-x86_64.tar.gz"
rm -rf "$STAGE"
mkdir -p "$STAGE/packaging/common" "$ROOT/dist"
for item in app.py config.py models.py routes.py helpers.py forms.py wsgi.py \
            gunicorn.conf.py requirements.txt VERSION README.md static templates utils; do
    cp -a "$ROOT/$item" "$STAGE/"
done
cp -a "$ROOT/packaging/common/." "$STAGE/packaging/common/"
cp "$ROOT/packaging/tarball/install.sh" "$ROOT/packaging/tarball/uninstall.sh" "$STAGE/"
chmod +x "$STAGE/install.sh" "$STAGE/uninstall.sh"
find "$STAGE" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$STAGE" -type f -name '*.pyc' -delete
tar -czf "$OUT" -C "$ROOT/build/tarball" "leobooks-${VERSION}"
echo "Gerado: $OUT"
