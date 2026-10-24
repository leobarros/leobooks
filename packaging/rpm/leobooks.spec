%global debug_package %{nil}
%global __strip /bin/true
%global _build_id_links none

Name:           leobooks
Version:        __VERSION__
Release:        1%{?dist}
Summary:        Caderno de leitura em Flask
License:        Proprietary
URL:            https://hub.docker.com/repository/docker/nickolback/leobooks
Source0:        leobooks-%{version}.tar.gz

BuildArch:      x86_64
# O venv traz bibliotecas nativas do Pillow; as dependências reais são
# declaradas abaixo, não inferidas dos .so empacotados.
AutoReqProv:    no
BuildRequires:  python3-devel
BuildRequires:  python3-pip
Requires:       python3
Requires:       python3-libs
Requires:       sqlite-libs
Requires:       ca-certificates
Requires:       python3-gobject
Requires:       gtk3
Requires:       webkit2gtk4.1
Requires:       libjpeg-turbo
Requires:       zlib

%description
LeoBooks é um caderno de leitura: livros, citações, resumos, insights,
tags e progresso em um aplicativo GTK/WebKit local. Inclui serviço
systemd, atalho no GNOME e dados
persistentes em /var/lib/leobooks.

%prep
%setup -q

%build
# O venv é criado no %install para ficar autocontido no pacote.

%install
rm -rf %{buildroot}
install -d %{buildroot}/opt/leobooks/app
install -d %{buildroot}/opt/leobooks/venv
cp app.py config.py models.py routes.py helpers.py forms.py wsgi.py \
   gunicorn.conf.py requirements.txt %{buildroot}/opt/leobooks/app/
cp -a static templates utils %{buildroot}/opt/leobooks/app/
find %{buildroot}/opt/leobooks/app -type d -name __pycache__ -prune -exec rm -rf {} +
python3 -m venv --copies %{buildroot}/opt/leobooks/venv
%{buildroot}/opt/leobooks/venv/bin/pip install --no-cache-dir -r requirements.txt

# O venv grava o caminho absoluto do buildroot em scripts/pyvenv.cfg.
# Relocaliza para o caminho final antes do check-buildroot do RPM.
VENV="%{buildroot}/opt/leobooks/venv"
grep -RIl --exclude-dir=__pycache__ "%{buildroot}" "$VENV" 2>/dev/null | while IFS= read -r file; do
    sed -i "s|%{buildroot}||g" "$file"
done
find "$VENV" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$VENV" -type f -name '*.pyc' -delete

install -d %{buildroot}/etc/leobooks
install -d %{buildroot}/usr/lib/systemd/system
install -d %{buildroot}/usr/bin
install -d %{buildroot}/usr/share/applications
install -d %{buildroot}/usr/share/metainfo
install -d %{buildroot}/usr/share/icons/hicolor/scalable/apps
install -d %{buildroot}/usr/share/doc/leobooks
install -m 0644 packaging/common/leobooks.service %{buildroot}/usr/lib/systemd/system/leobooks.service
install -m 0640 packaging/common/leobooks.env %{buildroot}/etc/leobooks/leobooks.env
install -m 0755 packaging/common/leobooks %{buildroot}/usr/bin/leobooks
install -m 0644 packaging/common/io.github.leobarros.LeoBooks.desktop %{buildroot}/usr/share/applications/io.github.leobarros.LeoBooks.desktop
install -m 0644 packaging/appstream/io.github.leobarros.LeoBooks.metainfo.xml %{buildroot}/usr/share/metainfo/io.github.leobarros.LeoBooks.metainfo.xml
install -m 0644 packaging/common/leobooks.svg %{buildroot}/usr/share/icons/hicolor/scalable/apps/leobooks.svg
install -m 0644 packaging/common/README.txt %{buildroot}/usr/share/doc/leobooks/README.txt
install -m 0644 README.md %{buildroot}/usr/share/doc/leobooks/README.md

%pre
getent group leobooks >/dev/null || groupadd -r leobooks
getent passwd leobooks >/dev/null || useradd -r -g leobooks -d /var/lib/leobooks -s /sbin/nologin leobooks

%post
install -d -o leobooks -g leobooks -m 0750 /var/lib/leobooks
install -d -o root -g leobooks -m 0750 /etc/leobooks
chown root:leobooks /etc/leobooks/leobooks.env
chmod 0640 /etc/leobooks/leobooks.env
if [ -d /run/systemd/system ]; then
    systemctl daemon-reload >/dev/null 2>&1 || :
    systemctl enable leobooks.service >/dev/null 2>&1 || :
    systemctl restart leobooks.service >/dev/null 2>&1 || :
fi

%preun
if [ "$1" -eq 0 ] && [ -d /run/systemd/system ]; then
    systemctl stop leobooks.service >/dev/null 2>&1 || :
    systemctl disable leobooks.service >/dev/null 2>&1 || :
fi

%postun
if [ -d /run/systemd/system ]; then
    systemctl daemon-reload >/dev/null 2>&1 || :
fi

%files
/opt/leobooks
%config(noreplace) /etc/leobooks/leobooks.env
/usr/bin/leobooks
/usr/lib/systemd/system/leobooks.service
/usr/share/applications/io.github.leobarros.LeoBooks.desktop
/usr/share/metainfo/io.github.leobarros.LeoBooks.metainfo.xml
/usr/share/icons/hicolor/scalable/apps/leobooks.svg
%doc /usr/share/doc/leobooks/README.txt
%doc /usr/share/doc/leobooks/README.md

%changelog
* Sat Oct 24 2026 LeoBooks <nickolback@users.noreply.github.com> - 1.0.2-1
- Renderização por software para evitar tela preta no WebKitGTK.
* Sat Oct 24 2026 LeoBooks <nickolback@users.noreply.github.com> - 1.0.1-1
- Aplicativo GTK/WebKit, metadados AppStream e capturas para a loja.
* Sat Oct 24 2026 LeoBooks <nickolback@users.noreply.github.com> - 1.0.0-1
- Pacote nativo inicial com systemd, atalho GNOME e dados persistentes.
