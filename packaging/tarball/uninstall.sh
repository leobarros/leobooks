#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Execute como root: sudo ./uninstall.sh" >&2
    exit 1
fi

if [ -d /run/systemd/system ]; then
    systemctl stop leobooks.service 2>/dev/null || true
    systemctl disable leobooks.service 2>/dev/null || true
fi

rm -f /usr/lib/systemd/system/leobooks.service
rm -f /usr/share/applications/leobooks.desktop
rm -f /usr/share/icons/hicolor/scalable/apps/leobooks.svg
rm -rf /opt/leobooks

if [ -d /run/systemd/system ]; then
    systemctl daemon-reload
fi

printf 'LeoBooks removido. Dados em /var/lib/leobooks e configuração em /etc/leobooks foram preservados.\n'
printf 'Para remover também esses dados: sudo rm -rf /var/lib/leobooks /etc/leobooks\n'
