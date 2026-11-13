# Diretrizes de desenvolvimento

## Estado atual: pacotes Linux pausados

**Não gerar pacotes Linux neste momento.** Enquanto esta instrução estiver
presente, não execute `./packaging/build-all.sh`, não crie `.deb`, `.rpm` ou
tarball e não publique releases de pacotes Linux. O foco é o app local e o
Docker.

A seção **Empacotamento** abaixo fica suspensa até que o usuário peça
explicitamente para retomar os pacotes. Retomar significa remover esta pausa e
atualizar os arquivos de agentes.

## Design system e mudanças de estilo

O guia de cores, temas, fontes, ícones, espaçamento e componentes está em
`docs/design-system.md`.

**Toda mudança de estilo precisa ser informada ao usuário e validada em
conjunto antes de ser implementada.** Não altere cores, tipografia, ícones,
espaçamentos ou componentes por conta própria, mesmo que pareça uma melhoria.
A proposta deve dizer o que muda, por quê e quais telas/temas serão afetados.

Depois da aprovação, valide tema claro e madrugada, desktop e mobile, capture
antes/depois e rode os testes local + Docker.

## Links, rotas e criação de telas

Toda mudança em link, rota, `url_for`, `endpoint`, `action` de formulário,
redirect, menu, modal ou criação de nova tela precisa incluir uma checagem de
regressão das funções já implementadas.

Antes de considerar a mudança pronta:

- procure referências ao endpoint/rota alterada em `templates/`, `routes.py`,
  `static/js/` e testes;
- confirme que links antigos continuam válidos ou que o redirecionamento foi
  criado;
- valide formulários, ações de menu, modais, navegação e retorno após salvar;
- rode a suíte completa;
- suba o projeto e percorra os fluxos afetados na aplicação real;
- repita o fluxo principal no Docker.

Uma tela nova ou link novo não pode quebrar rotas, botões, formulários ou
redirecionamentos existentes.

## Testes obrigatórios

Toda mudança — código, template, configuração, migração ou empacotamento — deve
ser validada **localmente e no Docker** antes de ser considerada concluída.

### 1. Local

```bash
.venv/bin/pytest -q
```

A suíte atual tem **114 testes**. Não considere a mudança pronta se houver
falhas.

**Além dos testes, suba o próprio projeto e veja a mudança acontecendo.** Use uma
instância temporária para não tocar no banco real:

```bash
LEOBOOKS_INSTANCE="$(mktemp -d)" LEOBOOKS_PORT=5057 ./run.sh
```

Abra `http://127.0.0.1:5057` e valide a tela/fluxo alterado na aplicação real,
não apenas no test client. Para mudanças de interface, faça a validação nos
temas claro e madrugada e em viewport móvel.

Não use `instance/` nem `/var/lib/leobooks` para esse teste.

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

## Empacotamento (suspenso enquanto a pausa acima estiver ativa)

Quando a pausa for removida, mudanças em `packaging/`, `VERSION`, `app.py`,
`models.py`, `routes.py` ou nas migrações também exigirão:

```bash
./packaging/build-all.sh
```

Os artefatos ficam em `dist/`. O `.deb` é validado em Debian 13 e o `.rpm` em
Fedora 42; quando possível, teste a instalação e o serviço, não apenas o build.

## Dados

Nunca use o banco real de `instance/` ou `/var/lib/leobooks` em testes de
mudança. Use `tmp_path` nos testes e `LEOBOOKS_INSTANCE` temporário em scripts.
