# Diretrizes de desenvolvimento

## Testes obrigatórios

Toda mudança — código, template, configuração, migração ou empacotamento — deve
ser validada **localmente e no Docker** antes de ser considerada concluída.

### 1. Local

```bash
.venv/bin/pytest -q
```

A suíte atual tem **108 testes**. Não considere a mudança pronta se houver
falhas.

Para mudanças de interface ou fluxo, valide também a página afetada no
navegador local.

### 2. Docker

Construa a imagem com o código alterado, recrie o container e verifique a
saúde:

```bash
docker compose build
docker compose up -d --force-recreate

for i in $(seq 1 10); do
  status="$(docker inspect --format '{{.State.Health.Status}}' leobooks-leobooks-1 2>/dev/null || echo starting)"
  [ "$status" = healthy ] && break
  sleep 3
done

docker compose ps
curl -fsS http://127.0.0.1:5059/healthz
```

O resultado esperado é `healthy` e HTTP **200**.

Para mudanças de interface, abra `http://127.0.0.1:5059` e valide o fluxo
principal no container, não apenas no servidor local.

## Empacotamento

Mudanças em `packaging/`, `VERSION`, `app.py`, `models.py`, `routes.py` ou nas
migrações também exigem:

```bash
./packaging/build-all.sh
```

Os artefatos ficam em `dist/`. O `.deb` é validado em Debian 13 e o `.rpm` em
Fedora 42; quando possível, teste a instalação e o serviço, não apenas o build.

## Dados

Nunca use o banco real de `instance/` ou `/var/lib/leobooks` em testes de
mudança. Use `tmp_path` nos testes e `LEOBOOKS_INSTANCE` temporário em scripts.
