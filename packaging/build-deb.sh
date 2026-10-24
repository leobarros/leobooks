#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${VERSION:-$(tr -d '[:space:]' < "$ROOT/VERSION")}"
ARCH="${ARCH:-$(dpkg --print-architecture)}"
BUILD="$ROOT/build/deb"
PKG="$BUILD/leobooks_${VERSION}_${ARCH}"
DIST="$ROOT/dist"

rm -rf "$PKG"
mkdir -p "$PKG/DEBIAN" "$PKG/opt/leobooks/app" "$PKG/opt/leobooks/venv" \
         "$PKG/etc/leobooks" "$PKG/usr/lib/systemd/system" \
         "$PKG/usr/bin" "$PKG/usr/share/applications" \
         "$PKG/usr/share/metainfo" \
         "$PKG/usr/share/icons/hicolor/scalable/apps" \
         "$PKG/usr/share/doc/leobooks" "$DIST"

cp "$ROOT/app.py" "$ROOT/config.py" "$ROOT/models.py" "$ROOT/routes.py" \
   "$ROOT/helpers.py" "$ROOT/forms.py" "$ROOT/wsgi.py" \
   "$ROOT/gunicorn.conf.py" "$ROOT/requirements.txt" "$PKG/opt/leobooks/app/"
cp -a "$ROOT/static" "$ROOT/templates" "$ROOT/utils" "$PKG/opt/leobooks/app/"
find "$PKG/opt/leobooks/app" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$PKG/opt/leobooks/app" -type f -name '*.pyc' -delete

PYTHONDONTWRITEBYTECODE=1 python3 -m venv "$PKG/opt/leobooks/venv"
"$PKG/opt/leobooks/venv/bin/pip" install --no-cache-dir -r "$ROOT/requirements.txt"

# O venv foi criado no diretório de staging; seus scripts (gunicorn, pip)
# precisam apontar para o caminho final /opt/leobooks/venv no pacote.
VENV="$PKG/opt/leobooks/venv"
grep -RIl --exclude-dir=__pycache__ -- "$PKG" "$VENV" 2>/dev/null | while IFS= read -r file; do
    sed -i "s|$PKG||g" "$file"
done

install -m 0644 "$ROOT/packaging/common/leobooks.service" "$PKG/usr/lib/systemd/system/leobooks.service"
install -m 0640 "$ROOT/packaging/common/leobooks.env" "$PKG/etc/leobooks/leobooks.env"
install -m 0755 "$ROOT/packaging/common/leobooks" "$PKG/usr/bin/leobooks"
install -m 0644 "$ROOT/packaging/common/io.github.leobarros.LeoBooks.desktop" "$PKG/usr/share/applications/io.github.leobarros.LeoBooks.desktop"
install -m 0644 "$ROOT/packaging/appstream/io.github.leobarros.LeoBooks.metainfo.xml" "$PKG/usr/share/metainfo/io.github.leobarros.LeoBooks.metainfo.xml"
install -m 0644 "$ROOT/packaging/common/leobooks.svg" "$PKG/usr/share/icons/hicolor/scalable/apps/leobooks.svg"
install -m 0644 "$ROOT/packaging/common/README.txt" "$PKG/usr/share/doc/leobooks/README.txt"
install -m 0644 "$ROOT/README.md" "$PKG/usr/share/doc/leobooks/README.md"

cat > "$PKG/DEBIAN/control" <<CONTROL
Package: leobooks
Version: ${VERSION}
Section: web
Priority: optional
Architecture: ${ARCH}
Maintainer: LeoBooks <nickolback@users.noreply.github.com>
Homepage: https://hub.docker.com/repository/docker/nickolback/leobooks
Depends: python3 (>= 3.13), python3-venv, ca-certificates, libsqlite3-0, libjpeg62-turbo, zlib1g, python3-gi, gir1.2-gtk-3.0, gir1.2-webkit2-4.1
Recommends: tesseract-ocr, tesseract-ocr-por
Installed-Size: $(du -sk "$PKG" | cut -f1)
Description: Caderno de leitura com janela GTK
 LeoBooks guarda livros, citações, resumos, insights, tags e progresso
 de leitura em um aplicativo GTK/WebKit local. Inclui serviço systemd,
 atalho no GNOME e dados persistentes em /var/lib/leobooks.
CONTROL

cat > "$PKG/DEBIAN/conffiles" <<'CONFFILES'
/etc/leobooks/leobooks.env
CONFFILES

install -m 0755 /dev/stdin "$PKG/DEBIAN/postinst" <<'POSTINST'
#!/bin/sh
set -e

if ! getent group leobooks >/dev/null; then
    groupadd --system leobooks
fi
if ! getent passwd leobooks >/dev/null; then
    useradd --system --gid leobooks --home-dir /var/lib/leobooks \
            --shell /usr/sbin/nologin leobooks
fi

install -d -o leobooks -g leobooks -m 0750 /var/lib/leobooks
install -d -o root -g leobooks -m 0750 /etc/leobooks
chown root:leobooks /etc/leobooks/leobooks.env
chmod 0640 /etc/leobooks/leobooks.env

if [ -d /run/systemd/system ]; then
    systemctl daemon-reload >/dev/null 2>&1 || true
    systemctl enable leobooks.service >/dev/null 2>&1 || true
    systemctl restart leobooks.service >/dev/null 2>&1 || true
fi
exit 0
POSTINST

install -m 0755 /dev/stdin "$PKG/DEBIAN/prerm" <<'PRERM'
#!/bin/sh
set -e
if [ "$1" = remove ] && [ -d /run/systemd/system ]; then
    systemctl stop leobooks.service >/dev/null 2>&1 || true
    systemctl disable leobooks.service >/dev/null 2>&1 || true
fi
exit 0
PRERM

install -m 0755 /dev/stdin "$PKG/DEBIAN/postrm" <<'POSTRM'
#!/bin/sh
set -e
if [ "$1" = purge ]; then
    rm -rf /var/lib/leobooks /etc/leobooks
fi
if [ -d /run/systemd/system ]; then
    systemctl daemon-reload >/dev/null 2>&1 || true
fi
exit 0
POSTRM

chmod 0755 "$PKG/DEBIAN/postinst" "$PKG/DEBIAN/prerm" "$PKG/DEBIAN/postrm"
chmod 0644 "$PKG/DEBIAN/control" "$PKG/DEBIAN/conffiles"

# root:root em todos os arquivos, inclusive no venv.
dpkg-deb --root-owner-group --build "$PKG" "$DIST/leobooks_${VERSION}_${ARCH}.deb"
echo "Gerado: $DIST/leobooks_${VERSION}_${ARCH}.deb"
