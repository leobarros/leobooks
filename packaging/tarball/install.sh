#!/bin/sh
# Instalador nativo para Debian/Fedora/Arch e outras distros com systemd.
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Execute como root: sudo ./install.sh" >&2
    exit 1
fi

SRC_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PREFIX="/opt/leobooks"
APP_DIR="$PREFIX/app"
VENV_DIR="$PREFIX/venv"
DATA_DIR="/var/lib/leobooks"
CONF_DIR="/etc/leobooks"
UNIT="/usr/lib/systemd/system/leobooks.service"

command -v python3 >/dev/null || {
    echo "Python 3 não encontrado. Instale python3." >&2
    exit 1
}

if ! getent group leobooks >/dev/null; then
    groupadd --system leobooks
fi
if ! getent passwd leobooks >/dev/null; then
    useradd --system --gid leobooks --home-dir "$DATA_DIR" \
            --shell /usr/sbin/nologin leobooks
fi

install -d -o leobooks -g leobooks -m 0750 "$DATA_DIR"
install -d -o root -g leobooks -m 0750 "$CONF_DIR"
install -d "$PREFIX"

rm -rf "$APP_DIR"
install -d "$APP_DIR"
for item in app.py config.py models.py routes.py helpers.py forms.py wsgi.py \
            gunicorn.conf.py requirements.txt static templates utils; do
    cp -a "$SRC_DIR/$item" "$APP_DIR/"
done
find "$APP_DIR" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$APP_DIR" -type f -name '*.pyc' -delete

rm -rf "$VENV_DIR"
PYTHONDONTWRITEBYTECODE=1 python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --no-cache-dir -r "$APP_DIR/requirements.txt"

install -m 0644 "$SRC_DIR/packaging/common/leobooks.service" "$UNIT"
if [ ! -f "$CONF_DIR/leobooks.env" ]; then
    install -m 0640 "$SRC_DIR/packaging/common/leobooks.env" "$CONF_DIR/leobooks.env"
fi
chown root:leobooks "$CONF_DIR/leobooks.env"
chmod 0640 "$CONF_DIR/leobooks.env"

install -d /usr/share/applications /usr/share/icons/hicolor/scalable/apps
install -m 0644 "$SRC_DIR/packaging/common/leobooks.desktop" /usr/share/applications/leobooks.desktop
install -m 0644 "$SRC_DIR/packaging/common/leobooks.svg" /usr/share/icons/hicolor/scalable/apps/leobooks.svg

if [ -d /run/systemd/system ]; then
    systemctl daemon-reload
    systemctl enable leobooks.service
    systemctl restart leobooks.service
fi

printf '\nLeoBooks instalado.\n'
printf 'Acesse: http://127.0.0.1:5057\n'
printf 'Config: %s/leobooks.env\n' "$CONF_DIR"
printf 'Dados:  %s\n' "$DATA_DIR"
printf 'Logs:   journalctl -u leobooks -f\n'
