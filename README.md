# LeoBooks

**Seu caderno de leitura.** Um aplicativo WSGI em Flask para guardar citações,
resumos e insights dos livros que você está lendo — com uma estante que parece
um caderno, não um painel de controle.

---

## O que é

O LeoBooks nasceu dos wireframes em `wireframe/` e das diretrizes em
`.github/copilot-instructions.md`. A proposta é simples: **capturar uma ideia
antes que ela fuja**. A partir do início, qualquer pensamento pode virar nota
com poucos toques, já ligado a um livro, uma página, um capítulo e tags.

O foco não é gamificar a leitura, e sim criar um lugar confortável para as
margens: citações preservadas com a fonte, resumos escritos com as suas
palavras, insights que atravessam livros diferentes.

### Uma identidade própria

Em vez do dashboard genérico de Bootstrap, o LeoBooks usa uma linguagem
editorial inspirada em papel, tinta e ex-libris:

- **Papel & tinta**: fundo quente com textura sutil, tipografia serifada
  (Fraunces + Newsreader) e detalhes de fólio, filetes e carimbos.
- **Capas generativas**: quando um livro não tem capa, o servidor desenha um
  SVG único a partir do título, do autor e de um hash — cada livro ganha uma
  composição própria, offline e sem depender de APIs.
- **Modo madrugada**: um tema escuro quente, pensado para leitura noturna, com
  contraste revisado e persistência no perfil + `localStorage`.
- **Navegação mobile de verdade**: barra inferior fixa, botão central de
  captura e áreas de toque confortáveis.
- **Bootstrap como base, não como molde**: grid, modais, dropdowns e utilidades
  do Bootstrap 5.3.8 são usados, mas a camada visual é inteiramente autoral.

---

## Funcionalidades

### Conta e acesso
- Cadastro, login, logout e sessão persistente (“continuar conectado”).
- Senha com **4 a 10 caracteres** (regra explícita do projeto), guardada com
  hash Scrypt do Werkzeug.
- Isolamento total: livros, notas, tags e imagens pertencem a uma conta e só
  são consultados com o `user_id` da sessão.
- **Administração de usuários**: além do cadastro público em `/register`, a
  conta administradora pode criar novas contas em **Ajustes → Usuários**, com
  nome, e-mail, senha inicial e opção de conceder acesso administrativo.
  Atalhos também aparecem no menu do usuário e no topo de Ajustes.
- **Tutorial de primeiro acesso** com opção de pular, persistido por conta e
  reversível em Ajustes. Cada conta começa com um livro de exemplo.


### Biblioteca
- CRUD completo de livros: título, autores, editora, ISBN, total de páginas,
  página atual, status (*Quero ler, Lendo, Lido, Abandonado*) e capa.
- Capa enviada como imagem (otimizada e sem EXIF), URL externa ou **busca em
  bases públicas** (Open Library e Google Books, com fallback no Goodreads para
  ISBNs brasileiros) por ISBN, título ou autor.
  A capa escolhida é baixada e guardada no servidor; sem capa, o LeoBooks gera
  uma capa editorial em SVG.
- Progresso de leitura, páginas restantes e atualização rápida da página ou
  pela **porcentagem do Kindle**. A localização do Kindle não é uma página; o
  app converte o percentual para a página equivalente e mostra a estimativa.
- Filtros por status, busca por título/autor/editora e ordenação.


### Notas, resumos e citações
- Três tipos: **Citação**, **Resumo** e **Insight**, com capítulo e página.
- Editor Markdown com barra de ferramentas, contador, pré-visualização segura e
  atalhos (`Ctrl+B`, `Ctrl+I`, `Ctrl+Enter`).
- Tags coloridas por nota; sugestões de tags existentes; até 8 por nota.
- Foto da página como anexo privado (servida apenas ao dono) e OCR opcional.
- Edição e exclusão pelo menu da nota, com confirmação customizada.
- Busca global em livros, autores, ISBN, conteúdo, capítulo e tags.
- Revisão diária de citações, com modo de leitura em cartão e “compartilhar
  como imagem” (PNG desenhado em Canvas, para redes sociais/histórias).

### Ajustes e dados
- Aparência clara/escura, persistida na conta e localmente.
- Perfil, troca de senha e exclusão definitiva da conta em cascata.
- Exportação do caderno em **Markdown** e **JSON**, além de exportação por livro.
- Backup completo em SQLite e restauração com validação de integridade —
  disponíveis apenas para a conta **administradora**. O primeiro usuário criado
  no servidor é administrador; assim o backup do banco, que contém todas as
  contas, não fica exposto a todos.
- OCR opcional: se `tesseract` + `pytesseract` estiverem instalados, o texto da
  foto é extraído; caso contrário, a foto continua sendo anexada à nota.

---

## Como rodar

Requisitos: Python 3.10+ (testado com 3.13), SQLite e um navegador moderno.

```bash
cd leobooks

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# sobe com Waitress (WSGI)
./run.sh
```

Acesse **http://127.0.0.1:5057**.

> A porta padrão é **5057**, escolhida para não colidir com os serviços usuais
> do homelab: 5000, 8000, 3000 e 8081 estão explicitamente fora do caminho, e a
> porta não é associada a serviços conhecidos de DevOps/SRE (Prometheus 9090,
> Grafana 3000, Kibana 5601, etc.). Se a 5057 já estiver ocupada, use
> `LEOBOOKS_PORT=5058 ./run.sh` — a 5058 também não é uma porta de serviço
> conhecido.

### Primeiro acesso e tutorial

Cada novo cadastro recebe **um livro de exemplo**, *A Arte da Guerra*, com capa
gerada e sem notas — ele pode ser excluído normalmente. O primeiro usuário do
servidor vira administrador.

No primeiro acesso, um tutorial de cinco passos apresenta a biblioteca, a
captura rápida, o progresso por página ou percentual do Kindle e as opções de
backup/exportação. Ele pode ser **pulado** a qualquer momento e revisto depois
em **Ajustes → Rever tutorial**.

É possível desligar o livro de exemplo com `LEOBOOKS_SAMPLE_BOOK=0`.

### Variáveis de ambiente

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `LEOBOOKS_HOST` / `HOST` | `127.0.0.1` | Interface de escuta. Use `0.0.0.0` para acessar na LAN. |
| `LEOBOOKS_PORT` / `PORT` | `5057` | Porta HTTP. |
| `LEOBOOKS_DATABASE` | `instance/leobooks.db` | Caminho do SQLite. |
| `DATABASE_URL` | — | URI SQLAlchemy alternativa (ex.: outro SQLite). |
| `SECRET_KEY` | gerada em `instance/.secret_key` | Chave de sessão/CSRF. |
| `LEOBOOKS_HTTPS` | `0` | `1` liga `Secure` nos cookies, HSTS e CSRF estrito. |
| `LEOBOOKS_CSP` | `1` | Liga/desliga o cabeçalho CSP. |
| `LEOBOOKS_SAMPLE_BOOK` | `1` | Entrega o livro de exemplo a cada novo cadastro. |
| `LEOBOOKS_COVER_LOOKUP` | `1` | Liga/desliga a busca de capas em APIs públicas. |
| `LEOBOOKS_LOOKUP_TIMEOUT` | `8` | Timeout em segundos para cada API de capas. |
| `LEOBOOKS_LOOKUP_MAX_BYTES` | `4194304` | Tamanho máximo da capa baixada (4 MB). |
| `LEOBOOKS_LOG_LEVEL` | `INFO` | Nível dos logs (`INFO`, `WARNING`, `ERROR`...). |
| `LEOBOOKS_AUDIT_LOG` | — | Caminho opcional para gravar a auditoria em arquivo com rotação. |
| `LEOBOOKS_DEBUG` | `0` | Modo debug do Flask (não usar exposto). |

Rodando atrás de HTTPS, use `LEOBOOKS_HTTPS=1`. O servidor de desenvolvimento
do Flask **não** é usado em produção: `run.sh` sobe Waitress com 4 threads. Para
Gunicorn (1 worker e 4 threads, para caber no teto de 512 MB):

```bash
.venv/bin/gunicorn -w 1 --threads 4 -b 127.0.0.1:5057 wsgi:app
```

Exemplo de serviço systemd:

```ini
[Unit]
Description=LeoBooks
After=network.target

[Service]
User=lsales
WorkingDirectory=/home/lsales/projetos/leobooks
Environment=LEOBOOKS_HTTPS=1
Environment=MALLOC_ARENA_MAX=2
ExecStart=/home/lsales/projetos/leobooks/.venv/bin/waitress-serve --listen=127.0.0.1:5057 --threads=4 wsgi:app
Restart=on-failure
MemoryMax=512M
MemorySwapMax=512M

[Install]
WantedBy=multi-user.target
```

### Docker / Docker Compose

Os arquivos de container estão na raiz: `Dockerfile`, `docker-compose.yml` e
`.env.example`. A imagem usa Python 3.13 slim, roda
como usuário **non-root** (`leobooks`, UID/GID 1000), com Gunicorn em 1 worker e
4 threads, `max-requests` para conter vazamentos, `mem_limit: 512m` no Compose,
healthcheck e volume persistente.

```bash
cp .env.example .env
# revise porta, bind e opções no .env
docker compose up -d --build
docker compose ps
docker compose logs -f leobooks
```

Acesse **http://127.0.0.1:5059** (porta publicada no host; dentro do container o
app continua na 5057).

- Por padrão o bind é `127.0.0.1`. Para acessar pela LAN, use
  `LEOBOOKS_BIND_ADDR=0.0.0.0` no `.env` — de preferência atrás de um proxy
  reverso com TLS.
- Se a 5059 estiver ocupada, troque `LEOBOOKS_PUBLISH_PORT` por outra porta livre.
- Atrás de HTTPS, defina `LEOBOOKS_HTTPS=1` para cookies `Secure`/HSTS.
- Os dados ficam no volume nomeado **`leobooks_leobooks_instance`**, montado em
  `/app/instance`: banco SQLite, uploads, capas, backups e a chave de sessão.
  `docker compose down` preserva o volume; `docker compose down -v` apaga tudo.
- O **primeiro cadastro** vira administrador e recebe o livro de exemplo;
  o tutorial de boas-vindas aparece no primeiro acesso e pode ser pulado.
- **OCR**: defina `INSTALL_OCR=true` no `.env` e rode
  `docker compose up -d --build`. A imagem fica maior, mas ganha Tesseract
  (`por` + `eng`) e `pytesseract`.
- **Migrar o banco local** para o volume (com o stack parado):

```bash
docker compose down
docker run --rm \
  -v leobooks_leobooks_instance:/data \
  -v "$PWD/instance":/src:ro \
  alpine sh -c "cp -a /src/. /data/ && chown -R 1000:1000 /data"
docker compose up -d
```

  Ajuste `1000:1000` se tiver mudado `APP_UID`/`APP_GID` e confirme o nome do
  volume com `docker volume ls` (ele leva o prefixo do projeto Compose).
  Alternativamente, troque o volume nomeado por um bind mount
  `./data:/app/instance` e ajuste as permissões do diretório.
- **Backup** do volume: use o botão de backup do app (admin), que usa a API de
  backup consistente do SQLite. Para copiar o arquivo manualmente, pare o
  container antes:
  `docker compose stop leobooks && docker compose cp leobooks:/app/instance/leobooks.db ./leobooks_backup.db && docker compose start leobooks`.
- **Atualizar** após mudanças no código:

```bash
docker compose build --pull
docker compose up -d
```


---

## Memória (teto de 512 MB)

O Compose aplica **`mem_limit: 512m` e `memswap_limit: 512m`**. O app também foi
ajustado para não chegar perto disso:

- **1 worker Gunicorn + 4 threads** (antes eram 8 threads), com reciclagem do
  worker a cada 2.000 requisições;
- `MALLOC_ARENA_MAX=2` para reduzir fragmentação do alocador;
- pool SQLite de **2 conexões + 2 de overflow**;
- relacionamentos carregados sob demanda e contadores via `COUNT(*)`: o
  dashboard não materializa todas as notas, e biblioteca/ajustes não carregam
  conteúdo de notas só para contar;
- revisão e citação do dia usam `COUNT` + `OFFSET`/`LIMIT`, sem carregar o
  caderno inteiro;
- uploads limitados a **8 MB** e **16 MP**; capas baixadas, a **4 MB**; a
  decodificação de imagem é serializada (uma por vez) para não somar picos de
  memória entre as 4 threads; OCR compartilha o mesmo lock;
- OCR é opcional e também serializado. Ele vem **desligado** por padrão
  (`INSTALL_OCR=false`); se ativar, monitore o consumo, pois o Tesseract pode
  usar bastante memória.

Medições feitas no container com o limite de 512 MB:

| Cenário | Memória |
| --- | --- |
| Ocioso, após healthcheck | ~65 MiB |
| 250 livros + 15.000 notas, navegando por início/biblioteca/ajustes/tags/revisão | pico de ~203 MiB (cgroup), sem OOM |

Para acompanhar no homelab:

```bash
docker stats $(docker compose ps -q leobooks)
```

O limite fica visível em `docker inspect`:

```bash
docker inspect $(docker compose ps -q leobooks) --format '{{.HostConfig.Memory}}'
# 536870912
```

Se você roda fora do Docker, o exemplo systemd acima inclui
`MemoryMax=512M`/`MemorySwapMax=512M`. O `run.sh` local não impõe cgroup; use o
systemd ou o Compose quando precisar do teto rígido.

---

## Logs e auditoria

As principais ações da aplicação geram **uma linha JSON por evento** no
`stdout` — pensada para `docker logs`, `journald`, Loki ou um coletor simples.
O acesso HTTP também aparece nos logs do Gunicorn/Waitress, mas a auditoria
registra *o que aconteceu no domínio*:

```json
{"timestamp":"2026-10-21T22:14:46.387Z","severity":"info","event":"audit","app":"leobooks","action":"book.progress","outcome":"success","request_id":"f24953efc098","ip":"127.0.0.1","method":"POST","path":"/books/45fba9b7-.../progress","duration_ms":8.7,"user_id":"dcd64f39-...","user":"ana@example.com","book_id":"45fba9b7-...","mode":"percent","page":171,"percent":42.0,"status":"READING"}
```

Eventos cobertos:

- autenticação (`auth.login`, `auth.login_failed`, `auth.register`, `auth.logout`);
- primeiro acesso (`onboarding.complete`, `onboarding.reset`);
- administração (`user.create`, `user.create_failed`);
- livros e leitura (`book.create`, `book.update`, `book.delete`, `book.progress`, `book.status`);
- notas e OCR (`note.create`, `note.update`, `note.delete`, `ocr.extract`);
- capas públicas (`cover.lookup`, `cover.download`, falhas incluídas);
- ajustes (`settings.profile`, `settings.password`, `settings.theme`);
- dados (`backup.download`, `backup.restore`, `account.delete`, exportações);
- segurança (`security.csrf_failure`, `security.access_denied`, `error.server`);
- inicialização (`app.start`).

Cada evento inclui `request_id`, IP, método, caminho, duração, usuário
(`user_id`/e-mail) quando autenticado e o resultado (`success`, `failure` ou
`denied`). O mesmo `request_id` é devolvido no cabeçalho **`X-Request-ID`**,
facilitando correlacionar um erro mostrado ao usuário com o log.

**O que não é registrado:** senhas, tokens CSRF, cookies, conteúdo das notas ou
o corpo de uploads. Títulos de livros, tipos de nota, contagens e IDs são
registrados para dar contexto.

### Ver os logs

```bash
# execução local
./run.sh

# Docker
docker compose logs -f leobooks

# apenas linhas JSON de auditoria (com jq instalado)
docker compose logs -f leobooks | jq -R 'fromjson? | select(.event == "audit")'
```

### Arquivo com rotação

Além do stdout, é possível gravar em arquivo (5 MB por arquivo, 3 backups):

```bash
# local
LEOBOOKS_AUDIT_LOG=instance/logs/audit.log ./run.sh

# Docker: no .env
LEOBOOKS_AUDIT_LOG=/app/instance/logs/audit.log
```

O caminho relativo é resolvido a partir da raiz do app; no Docker, use o volume
`/app/instance` para persistir. O nível pode ser ajustado com
`LEOBOOKS_LOG_LEVEL=INFO`.

---

## Segurança

- **CSRF** em todos os formulários e no `fetch` do tema/OCR via `Flask-WTF` +
  `CSRFProtect`.
- **XSS**: Markdown convertido com `markdown` e sempre passado por
  `bleach.clean()` com whitelist restrita (`utils/markdown_helper.py`). Os testes
  cobrem `<script>`, `onerror`, `javascript:` e `<iframe>`.
- **SQL Injection**: exclusivamente ORM/consultas parametrizadas.
- **Uploads**: apenas JPG/PNG/WebP; o Pillow valida, reescreve e remove EXIF;
  arquivos ficam em `instance/` e são servidos por rotas autenticadas que
  verificam a propriedade.
- **Capas públicas**: as URLs candidatas são assinadas com expiração; o download
  aceita somente hosts conhecidos (Open Library, Google Books, Goodreads/Amazon
  Media e redirects do Internet Archive), valida o host final, o tipo de conteúdo
  e o tamanho, e reprocessa a imagem com Pillow. Nenhuma URL arbitrária enviada
  pelo cliente é buscada. As consultas recebem somente ISBN, título e autor.
- **CSP** com nonce por requisição, `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy` e `Permissions-Policy`.
- **Sessão**: cookie `HttpOnly`, `SameSite=Lax`, sessão renovada no login para
  evitar fixação; senhas com Scrypt.
- **Backup**: restrito ao administrador; a restauração valida cabeçalho SQLite,
  `integrity_check` e tabelas obrigatórias, guarda uma cópia de segurança antes
  de substituir o banco e encerra a sessão.
- **Exclusão de conta** em cascata para livros, notas, tags, associações e
  imagens.

---

## Testes

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
```

A suíte cobre rotas WSGI, validação de senha, CSRF, isolamento entre usuários,
sanitização de Markdown/XSS, uploads, OCR (mockado), busca de capas públicas,
tokens assinados, bloqueio de SSRF, tags, exportação, backup/restauração e
exclusão de conta. Estado atual: **96 testes passando**.

---

## Estrutura

```text
leobooks/
├── Dockerfile              # imagem Python slim + Gunicorn (non-root)
├── docker-compose.yml      # stack do homelab, volume e healthcheck
├── .env.example            # variáveis do Compose
├── app.py                  # application factory, CSP, erros, migrações
├── config.py               # configuração e segredos
├── models.py               # User, Book, Note, Tag, note_tags
├── routes.py               # blueprints auth/main/books/notes/settings
├── helpers.py              # sessão, datas, tags, streak, decorators
├── forms.py                # formulários Flask-WTF e validações
├── wsgi.py                 # ponto de entrada para Waitress/Gunicorn
├── run.sh                  # execução local com Waitress
├── utils/
│   ├── markdown_helper.py  # Markdown + sanitização XSS
│   ├── cover_art.py        # capas generativas em SVG
│   ├── book_lookup.py      # Open Library/Goodreads/Google + download validado
│   ├── audit.py            # logs JSON de auditoria + rotação
│   ├── media.py            # imagem segura com Pillow
│   └── ocr.py              # OCR opcional
├── static/
│   ├── css/style.css       # design system "papel & tinta"
│   ├── css/fonts.css       # fontes self-hosted
│   ├── js/app.js           # tema, modal, editor, capas, share, OCR
│   ├── fonts/              # Fraunces, Newsreader, Inter
│   ├── img/favicon.svg
│   └── vendor/             # Bootstrap 5.3.8 + Bootstrap Icons 1.13.1
├── templates/
│   ├── base.html, layout.html
│   ├── auth/{login,register}.html
│   ├── dashboard.html, library.html, book_detail.html, book_form.html
│   ├── tags.html, review.html, search.html, settings.html, users.html
│   ├── errors/error.html
│   └── partials/           # navegação, macros, modais
├── tests/
└── wireframe/              # referências originais
```

Todos os assets de interface (Bootstrap, Bootstrap Icons, fontes) são servidos
localmente; nenhuma CDN é necessária em runtime.

---

## Limites conhecidos e próximos passos

- **OCR** é opcional por design. Para ativar:
  `sudo apt install tesseract-ocr tesseract-ocr-por && .venv/bin/pip install pytesseract`.
- **PDF**: a exportação atual é Markdown/JSON; para PDF, use a impressão do
  navegador (o CSS tem uma camada `@media print`) ou converta o Markdown.
- **Offline-first** (RNF03) ainda não implementado com service worker; o app
  depende do servidor local.
- **Busca de capas** depende de serviços externos (Open Library, Google Books e
  o fallback público do Goodreads) e pode falhar, demorar ou ser limitada por
  rate limit/anti-bot; o app continua funcional e usa a capa gerada como
  fallback. Não é necessária chave de API. O recurso pode ser desligado com
  `LEOBOOKS_COVER_LOOKUP=0`.
- SQLite atende bem um homelab pessoal; para múltiplos servidores simultâneos,
  seria necessário migrar para PostgreSQL e um storage de sessão compartilhado.

---

Feito para ler devagar e anotar com intenção.
