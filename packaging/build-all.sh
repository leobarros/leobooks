#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$ROOT/packaging/build-deb.sh"
"$ROOT/packaging/build-tarball.sh"
"$ROOT/packaging/build-rpm.sh"

VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
cd "$ROOT/dist"
sha256sum leobooks_${VERSION}_*.deb leobooks-${VERSION}-*.rpm leobooks-${VERSION}-linux-*.tar.gz > SHA256SUMS
cat > BUILD-INFO.txt <<INFO
LeoBooks ${VERSION} — pacotes nativos
Gerado em: $(date -Is)
Debian: amd64, Python 3.13
Fedora: x86_64, Fedora 42 / Python 3.13
Tarball: instalador nativo (Python 3.10+ no destino)
Docker: nickolback/leobooks:latest

Arquivos:
$(ls -1 leobooks_${VERSION}_*.deb leobooks-${VERSION}-*.rpm leobooks-${VERSION}-linux-*.tar.gz 2>/dev/null)
INFO
echo "Artefatos e checksums em $ROOT/dist"
