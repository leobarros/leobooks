# Registro de mudanças

## Não lançado

- README reescrito como um percurso da leitora fictícia Mariana, cobrindo
  estante, citação no celular, livro digital, busca, compartilhamento e backup.

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
