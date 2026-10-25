# Registro de mudanças

## Não lançado

- README reorganizado em **O que é**, **Propósito**, **Como instalar**,
  **Como usar**, **Dúvidas frequentes** e **Técnico**.
- Capturas atualizadas na versão atual com a conta fictícia **Mariana Sales**,
  incluindo desktop, celular, tutorial e tema madrugada.

## 1.0.7 — 2026-10-24

- Removida a barra interna; a janela usa apenas a decoração e o botão Fechar do
  GNOME.
- Ativado cache de página e modelo de cache do WebKit.
- Assets estáticos agora têm `Cache-Control: max-age=3600`.
- Adicionado teste de regressão para o cache dos assets.

## 1.0.6 — 2026-10-24

- O aplicativo GTK voltou a usar a janela e o renderizador WebKit padrão, que
  funcionam no Debian/GNOME; o modo de software agora é opcional via
  `LEOBOOKS_GTK_SAFE=1`.
- Removido o `Gtk.ApplicationWindow`/headerbar que diferia do teste mínimo.
- Mantidos os botões Recarregar e Fechar em uma barra interna.

## 1.0.5 — 2026-10-24

- Corrigido o app nativo para criar os dados em `LEOBOOKS_INSTANCE`
  (`/var/lib/leobooks`) em vez de `/opt/leobooks/app/instance`, que é somente
  leitura no serviço systemd.
- Adicionado teste de regressão para o diretório de dados configurado.

## 1.0.4 — 2026-10-24

- Adicionado botão explícito **Fechar** na barra da janela GTK.
- Mantido o botão de recarregar à esquerda.

## 1.0.3 — 2026-10-24

- Corrigido o `.deb` que empacotava scripts do venv com shebang do diretório
  temporário de build. O serviço caía com `203/EXEC` e o app GTK ficava sem a
  API local.
- Corrigida a página de erro para não depender de uma URL indisponível.

## 1.0.2 — 2026-10-24

- Corrigida a tela preta do aplicativo GTK no Debian/GNOME com Wayland, GPU
  virtual ou drivers NVIDIA, forçando o renderizador de software do WebKitGTK.
- Adicionado botão nativo de recarregar a interface.
- O serviço systemd e o banco SQLite local permanecem iguais.

## 1.0.1 — 2026-10-24

- Pacotes nativos agora instalam um aplicativo GTK/WebKit em vez de abrir o
  navegador externo.
- Adicionados `leobooks`, atalho GNOME e metadados AppStream.
- Adicionadas capturas PNG para GNOME Software/loja Debian.
- Dependências GTK 3 e WebKitGTK 4.1 adicionadas ao Debian e Fedora; documentadas
  no tarball para Arch.
- O serviço systemd e o banco SQLite local continuam iguais.

## 1.0.0 — 2026-10-24

- Empacotamento Debian 13 (`amd64`) com serviço systemd, atalho GNOME e dados em
  `/var/lib/leobooks`.
- Empacotamento Fedora 42 (`x86_64`) com as mesmas convenções.
- Tarball instalável para Arch e outras distros com Python 3/systemd.
- O diretório de dados agora pode ser configurado com `LEOBOOKS_INSTANCE`.
- Docker permanece como opção de implantação, sem alteração de uso.

### Empacotamento

Artefatos gerados em `dist/`:

- `leobooks_1.0.0_amd64.deb`
- `leobooks-1.0.0-1.fc42.x86_64.rpm`
- `leobooks-1.0.0-linux-x86_64.tar.gz`
- `SHA256SUMS` e `BUILD-INFO.txt`

Commits/deploys futuros devem atualizar `VERSION`, regenerar os pacotes e
manter este registro.
