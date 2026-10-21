# LeoBooks

**Seu caderno de leitura.** Um lugar tranquilo para guardar citações, resumos e
ideias dos livros que você está lendo — com uma estante que parece um caderno,
não um painel de controle.

![Tela inicial do LeoBooks](docs/screenshots/inicio.webp)

> As imagens abaixo usam uma conta fictícia e livros de exemplo. Nenhum dado
> real de leitor aparece nelas.

## Um lugar para as ideias que a leitura deixa

O LeoBooks reúne, em uma só tela, o livro que você está lendo, o trecho que
marcou e o pensamento que veio depois. Cada nota fica ligada à página, ao
capítulo e às tags que você escolher.

- **Estante visual** com capas, andamento e status de cada leitura.
- **Três tipos de nota:** citação, resumo e insight.
- **Progresso pela página ou pelo percentual do Kindle.**
- **Tags que atravessam livros**, busca e uma revisão diária de citações.
- **Tema claro ou madrugada**, para ler e anotar em qualquer hora.
- **Seus dados no seu servidor**, com exportação e backup.

## Veja o app

### Sua estante

![Biblioteca do LeoBooks com capas e filtros](docs/screenshots/biblioteca.webp)

### Cada livro, com suas margens

![Detalhe de um livro com progresso e notas](docs/screenshots/livro.webp)

### Uma nota em poucos segundos

![Modal de nova nota com editor Markdown](docs/screenshots/nota.webp)

### No celular

<p align="center">
  <img src="docs/screenshots/mobile.webp" alt="Tela inicial do LeoBooks no celular" width="300">
  <img src="docs/screenshots/mobile-nota.webp" alt="Nova nota no celular" width="300">
</p>

### E quando a noite chega

![LeoBooks no tema escuro](docs/screenshots/tema-escuro.webp)

## Comece a usar

### Com Docker (recomendado)

Você só precisa de **Docker** e **Docker Compose** no servidor.

```bash
# dentro da pasta do projeto
cp .env.example .env

# opcional: edite porta, endereço e outras opções no .env
docker compose up -d --build
```

Abra **[http://127.0.0.1:5059](http://127.0.0.1:5059)** e crie sua conta.

Pronto. A primeira conta criada é a administradora do servidor. Na primeira
entrada, o LeoBooks apresenta um tutorial de cinco passos — você pode fazê-lo
ou clicar em **Pular tutorial**.

Se a imagem já estiver publicada no Docker Hub, também é possível baixá-la:

```bash
docker compose pull
docker compose up -d --no-build
```

O repositório configurado é
**[nickolback/leobooks](https://hub.docker.com/repository/docker/nickolback/leobooks)**.

### Sem Docker

Para rodar direto no computador ou servidor, com **Python 3.10+**:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./run.sh
```

Acesse **http://127.0.0.1:5057**.

Para parar, use `Ctrl+C`. Os dados ficam em `instance/`.

### O primeiro acesso

Ao criar a conta, você recebe um livro de exemplo — *A Arte da Guerra* — para
explorar. Ele não tem notas e pode ser excluído quando quiser começar a sua
própria estante.

![Tutorial de boas-vindas do LeoBooks](docs/screenshots/tutorial.webp)

O tutorial mostra a biblioteca, a captura rápida, o progresso de leitura e as
opções de dados. Ele pode ser **pulado** e revisto depois em
**Ajustes → Rever tutorial**.

## Como usar

### 1. Coloque um livro na estante

Vá em **Biblioteca → Adicionar livro**. Informe título, autor e, se quiser,
editora, ISBN e total de páginas.

- A busca de capas consulta bases públicas por ISBN, título ou autor.
- Se nenhuma capa for encontrada, o LeoBooks desenha uma capa editorial para o
  livro — o caderno continua bonito e funcionando offline.
- Você também pode enviar uma foto da capa.

### 2. Registre o que ficou

Use **Nova nota rápida** na lateral, no celular, ou **Adicionar nota** dentro de
um livro. Escolha o tipo:

- **Citação:** o trecho exato, com página e capítulo.
- **Resumo:** as ideias do capítulo com suas palavras.
- **Insight:** uma conexão, pergunta ou pensamento que ficou.

O editor aceita Markdown. Você pode usar **negrito**, *itálico*, listas, links e
citações; há uma prévia antes de guardar. As tags ajudam a reencontrar o assunto
depois — por exemplo, `#atenção`, `#clássicos` ou `#política`.

Se quiser, anexe uma foto da página. O OCR de texto é opcional: quando o
servidor tem Tesseract instalado, ele tenta trazer o texto da foto; quando não,
a imagem continua anexada normalmente.

### 3. Acompanhe seu ritmo

No detalhe do livro, atualize o progresso de duas formas:

- **Página:** informe a página atual.
- **% Kindle:** informe o percentual que aparece no rodapé do Kindle. O app
  calcula a página equivalente e mostra a estimativa.

Ao chegar a 100%, o livro é marcado como **Lido**. Você também pode mudar o
status manualmente para *Quero ler*, *Lendo*, *Lido* ou *Abandonado*.

### 4. Reencontre ideias

- **Busca** procura em títulos, autores, ISBN, conteúdo das notas, capítulos e
  tags.
- **Tags** mostram os fios que atravessam livros diferentes.
- **Revisão** traz uma citação para reler, com opção de compartilhar como
  imagem.
- O **início** reúne o que está aberto agora, a citação do dia e seu ritmo de
  leitura.

### 5. Deixe do seu jeito

- Alterne entre **tema claro e madrugada** na lateral ou no topo.
- Em **Ajustes**, edite seu perfil, troque a senha, exporte o caderno em
  Markdown/JSON ou baixe um backup SQLite.
- A conta administradora também pode criar outras contas e restaurar backups.

## Perguntas frequentes

**Onde ficam meus dados?**
No servidor onde o LeoBooks está rodando. No Docker, ficam em um volume
persistente; sem Docker, em `instance/`. Não há envio para uma nuvem do
LeoBooks.

**Como atualizo o app?**
Com Docker:

```bash
docker compose pull
docker compose up -d --no-build
```

Se estiver compilando localmente:

```bash
docker compose build --pull
docker compose up -d
```

O volume com seus dados é preservado.

**Como apago tudo?**
Você pode excluir sua conta em **Ajustes → Excluir conta**. Para apagar também o
volume do Docker, use `docker compose down -v` — atenção: isso remove o banco,
as capas e todos os backups locais.

**Esqueci minha senha. E agora?**
O LeoBooks não envia e-mail de recuperação. Peça à conta administradora para
criar uma nova conta, ou remova o volume e comece de novo se for um ambiente de
testes.

**Funciona no Kindle?**
Use o navegador do celular ou computador; o app não é um aplicativo nativo do
Kindle. O progresso pode ser informado pela porcentagem exibida no aparelho.

**Preciso estar sempre conectado à internet?**
Não. O LeoBooks roda no seu servidor. A internet só é usada quando você pede
para buscar capas em bases públicas.

**Por que apareceu um livro que eu não cadastrei?**
É o livro de exemplo do primeiro acesso. Ele pode ser excluído normalmente em
**Biblioteca**.

## Privacidade

- Cada conta vê somente os próprios livros, notas, tags e imagens.
- Não há telemetria nem rastreadores de terceiros.
- A busca de capas envia apenas ISBN, título e autor para Open Library, Google
  Books e, como fallback, Goodreads. O conteúdo das suas notas nunca é enviado.
- Os logs de auditoria ficam no servidor e não registram senhas, tokens nem o
  conteúdo das notas.
- O backup do banco contém todas as contas e é restrito à administradora.

---

<details>
<summary><strong>Detalhes técnicos, Docker Hub e configuração avançada</strong></summary>

### Stack

Flask 3 + SQLite + Jinja + Bootstrap 5 local. Em produção, Waitress no modo
local ou Gunicorn no Docker (1 worker, 4 threads). Os assets de interface
(Bootstrap, ícones e fontes) são servidos localmente.

### Segurança

- CSRF em todos os formulários e requisições de escrita.
- Markdown convertido e sanitizado contra XSS.
- Senhas com hash Scrypt do Werkzeug.
- Uploads reescritos com Pillow, sem EXIF, servidos por rotas autenticadas.
- Busca de capas com allowlist de hosts, URLs assinadas e limite de tamanho.
- CSP, `X-Content-Type-Options`, `X-Frame-Options` e `Referrer-Policy`.
- Restauração de backup validada e restrita à administradora.

### Memória

O Compose aplica **`mem_limit: 512m`**. Medições no container:

| Cenário | Memória |
| --- | --- |
| Ocioso | ~65 MiB |
| 250 livros + 15.000 notas navegando pelo app | pico de ~203 MiB, sem OOM |

As consultas do dashboard e dos Ajustes usam contagens SQL, sem materializar
todas as notas. Imagens e OCR são processados um por vez para manter o pico
previsível.

### Logs

As ações principais geram linhas JSON de auditoria no `stdout`, com
`request_id`, usuário, IP e resultado. Senhas, tokens e conteúdo das notas não
são registrados.

```bash
docker compose logs -f leobooks
```

### Variáveis principais

| Variável | Padrão | Para que serve |
| --- | --- | --- |
| `LEOBOOKS_PORT` | `5057` | Porta interna/local. |
| `LEOBOOKS_BIND_ADDR` | `127.0.0.1` | Endereço publicado pelo Compose. |
| `LEOBOOKS_PUBLISH_PORT` | `5059` | Porta no host. |
| `LEOBOOKS_SAMPLE_BOOK` | `1` | Cria o livro de exemplo em cada cadastro. |
| `LEOBOOKS_COVER_LOOKUP` | `1` | Liga/desliga a busca de capas. |
| `LEOBOOKS_IMAGE_TAG` | `latest` | Tag da imagem `nickolback/leobooks`. |
| `LEOBOOKS_HTTPS` | `0` | Ativa cookies seguros quando atrás de HTTPS. |
| `LEOBOOKS_LOG_LEVEL` | `INFO` | Nível dos logs. |
| `INSTALL_OCR` | `false` | Instala Tesseract na imagem (aumenta tamanho/memória). |

O arquivo [.env.example](.env.example) traz todas as opções comentadas.

### Publicar a imagem no Docker Hub

O Compose já aponta para `nickolback/leobooks`:

```bash
docker login
docker compose build
docker compose push
```

Para uma release versionada:

```bash
LEOBOOKS_IMAGE_TAG=1.0.0 docker compose build
LEOBOOKS_IMAGE_TAG=1.0.0 docker compose push
```

O repositório é
https://hub.docker.com/repository/docker/nickolback/leobooks.

### Testes

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
```

Estado atual: **96 testes passando** — rotas, CSRF, isolamento entre contas,
sanitização de Markdown, uploads, busca de capas, backup, tutorial e exclusão de
conta.

### Limites conhecidos

- Não há recuperação de senha por e-mail.
- OCR depende de Tesseract instalado e vem desligado por padrão.
- A exportação é Markdown/JSON; para PDF, use a impressão do navegador.
- A busca de capas depende de serviços externos e pode falhar; a capa gerada é
  o fallback.
- SQLite atende bem um servidor pessoal; para várias instâncias simultâneas,
  seria necessário migrar para PostgreSQL.

### Estrutura resumida

```text
app.py, routes.py, models.py, helpers.py, forms.py
utils/            Markdown, capas, imagens, OCR, auditoria
templates/        telas e componentes Jinja
static/           CSS, JS, fontes e Bootstrap local
tests/            suíte de testes
wireframe/        referências originais de design
```

</details>

---

Feito para ler devagar e anotar com intenção.
