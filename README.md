# LeoBooks

**Seu caderno de leitura.** Um lugar tranquilo para guardar citações, resumos e
ideias dos livros que você está lendo — com uma estante que parece um caderno,
não um painel de controle.

![Tela inicial do LeoBooks com a conta de Mariana](docs/screenshots/inicio.webp)

> As imagens usam a conta fictícia **Mariana Costa** e livros de exemplo.
> Nenhum dado real de leitor aparece nelas.

## O que é

O LeoBooks é um caderno de leitura que reúne, em uma só tela, o livro que você
está lendo, o trecho que marcou e o pensamento que veio depois. Cada nota fica
ligada à página, ao capítulo e às tags que você escolher.

- **Estante visual** com capas, andamento e status de cada leitura.
- **Três tipos de nota:** citação, resumo e insight.
- **Livro físico ou digital**, cada um com sua própria forma de progresso.
- **Tags que atravessam livros**, busca sem acentos e revisão de citações.
- **Tema claro ou madrugada**, para ler e anotar em qualquer hora.
- **Dados no seu servidor**, com exportação e backup completo em um arquivo ZIP.
- **Aplicativo GTK no GNOME** ou acesso pelo navegador em outros dispositivos.

![Biblioteca do LeoBooks com capas e filtros](docs/screenshots/biblioteca.webp)

## Propósito

O LeoBooks existe para lembrar que leitura não é uma lista de tarefas.

Ele foi desenhado para ser aberto por alguns minutos, guardar uma passagem e
sumir — sem feed, ranking de leituras, notificações de produtividade ou
telemetria. A estante deve parecer um caderno, não um dashboard.

> “Eu não quero um relatório do quanto li. Quero reencontrar a frase que me fez
> parar.”
>
> — Mariana, leitora fictícia que aparece nas capturas

Os princípios são simples:

- **Uma ideia de cada vez:** escrever uma nota deve ser mais rápido do que
  procurar um caderno.
- **Contexto importa:** página, capítulo, livro e tags ficam juntos.
- **Seus dados são seus:** tudo fica no seu servidor, em SQLite.
- **Funciona no seu ritmo:** papel, Kindle, celular ou computador; o caderno
  acompanha você.

## Como instalar

Escolha a forma que combina com o seu servidor ou computador.

### Debian 13 / GNOME

O `.deb` instala o aplicativo GTK, o serviço local e o atalho no menu do GNOME:

```bash
sudo apt install ./leobooks_1.0.7_amd64.deb
sudo systemctl status leobooks
```

Abra **LeoBooks** no menu do GNOME ou execute:

```bash
leobooks
```

O aplicativo usa a janela e o botão de fechar do próprio GNOME. O banco fica em
`/var/lib/leobooks` e a configuração em `/etc/leobooks/leobooks.env`.

### Fedora 42

```bash
sudo dnf install ./leobooks-1.0.7-1.fc42.x86_64.rpm
sudo systemctl status leobooks
```

Em Fedora com `yum`, o comando equivalente é:

```bash
sudo yum install ./leobooks-1.0.7-1.fc42.x86_64.rpm
```

### Arch e outras distros

```bash
tar -xzf leobooks-1.0.7-linux-x86_64.tar.gz
cd leobooks-1.0.7
sudo ./install.sh
```

No Arch, instale antes as dependências gráficas:

```bash
sudo pacman -S python-gobject gtk3 webkit2gtk-4.1
```

O instalador cria o venv no destino; o alvo precisa de Python 3.10+ e acesso ao
PyPI durante a instalação.

### Docker (servidor)

Para usar pelo navegador, inclusive em outro computador ou no Tailscale:

```bash
docker compose up -d --build
```

A porta **0.0.0.0:5059** já está definida no `docker-compose.yml`. Abra
**[http://127.0.0.1:5059](http://127.0.0.1:5059)** e crie a primeira conta.

Se a imagem já estiver publicada:

```bash
docker compose pull
docker compose up -d --no-build
```

A imagem fica em
**[nickolback/leobooks](https://hub.docker.com/repository/docker/nickolback/leobooks)**.

O Docker e a instalação nativa têm bancos separados: o Docker usa o volume
`leobooks_instance`; o app nativo usa `/var/lib/leobooks`. Para migrar dados,
use o backup em ZIP em **Ajustes → Dados e backup**.

### Rodando direto com Python

Para desenvolvimento ou para testar sem instalar:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./run.sh
```

Acesse **http://127.0.0.1:5057**. Os dados ficam em `instance/`.

### Acesso pelo Tailscale

Por segurança, o serviço nativo escuta apenas em `127.0.0.1`. Para acessar de
outro dispositivo do tailnet, edite `/etc/leobooks/leobooks.env`:

```env
LEOBOOKS_BIND=0.0.0.0
```

Depois reinicie:

```bash
sudo systemctl restart leobooks
```

Descubra o IP e teste:

```bash
tailscale ip -4
curl -I "http://$(tailscale ip -4):5057/healthz"
```

No Docker, a porta já é publicada em `0.0.0.0:5059`; use
`http://100.x.y.z:5059`. Enquanto `LEOBOOKS_HTTPS=0`, use `http://`, não
`https://`.

### Primeiro acesso

A primeira conta criada é a administradora do servidor. Você recebe o livro de
exemplo *A Arte da Guerra* para explorar; ele pode ser excluído normalmente.

![Tutorial de boas-vindas do LeoBooks](docs/screenshots/tutorial.webp)

O tutorial pode ser pulado e revisto depois em **Ajustes → Rever tutorial**.

## Como usar

Mariana é professora de história, lê em papel e no Kindle e usa o celular no
caminho da escola. Ela não quer registrar tudo: quer guardar o que vale a pena
reler.

### 1. Coloque um livro na estante

Em **Biblioteca → Adicionar livro**, informe título e autor e escolha o formato:

- **Livro físico:** o progresso é marcado pela página impressa.
- **Livro digital:** o progresso é marcado pelo percentual exibido no aparelho.
  O total de páginas é opcional e serve apenas para estimar a página equivalente.

A busca de capas consulta bases públicas por ISBN, título ou autor. Se não
encontrar, o LeoBooks desenha uma capa editorial — o caderno continua bonito e
funcionando offline. Você também pode enviar uma foto da capa.

![Escolha entre livro físico e digital](docs/screenshots/formato.webp)

### 2. Guarde o que ficou

Use **Nova nota rápida** na lateral, no celular, ou **Adicionar nota** dentro de
um livro. Escolha o tipo:

- **Citação:** o trecho exato, com página e capítulo.
- **Resumo:** as ideias do capítulo com suas palavras.
- **Insight:** uma conexão, pergunta ou pensamento que ficou.

O editor aceita Markdown: negrito, itálico, listas, links e citações. As tags
ajudam a reencontrar o assunto depois — por exemplo, `#política`, `#clássicos`
ou `#história`.

Se quiser, anexe uma foto da página. O OCR é opcional: quando o servidor tem
Tesseract instalado, ele tenta trazer o texto da foto; quando não, a imagem
continua anexada normalmente.

![Modal de nova nota com editor Markdown](docs/screenshots/nota.webp)

### 3. Acompanhe seu ritmo

Cada formato tem sua mecânica:

- **Livro físico:** informe a página atual. O app calcula o percentual e quanto
  falta para o fim.
- **Livro digital:** informe o percentual que aparece no rodapé do aparelho.
  Se você preencheu o total de páginas, o app mostra também a página
  equivalente aproximada. A “localização” do leitor digital não é uma página.

Ao chegar a 100%, o livro é marcado como **Lido**. Você também pode mudar o
status manualmente para *Quero ler*, *Lendo*, *Lido* ou *Abandonado*. Se trocar
de formato no meio da leitura, o progresso existente é convertido.

![Detalhe de um livro com progresso e notas](docs/screenshots/livro.webp)

### 4. Reencontre ideias

- **Busca** procura em títulos, autores, ISBN, conteúdo das notas, capítulos e
  tags — e ignora acentos: `principe` encontra “O Príncipe”.
- **Tags** mostram os fios que atravessam livros diferentes.
- **Revisão** traz uma citação para reler, com opção de compartilhar como
  imagem. O arquivo termina em `-leobooks.png`, por exemplo
  `o-principe-capitulo-xxi-pagina-74-leobooks.png`.

### 5. Deixe do seu jeito

- Alterne entre **tema claro e madrugada** na lateral ou no topo.
- Em **Ajustes**, edite o perfil, troque a senha, exporte o caderno em
  Markdown/JSON ou baixe um **backup completo**.
- A conta administradora também cria outras contas e restaura backups.

### 6. Leve tudo com você

Em **Ajustes → Dados e backup**, a administradora baixa **um único arquivo
`.zip`** com banco, capas, fotos e manifesto:

```text
leobooks_backup_AAAAMMDD_HHMMSS.zip
├── leobooks.db       # banco SQLite consistente
├── covers/           # capas
├── uploads/          # fotos das notas
└── manifest.json     # formato, contagens e checksums
```

Para restaurar, envie o mesmo `.zip` em **Restaurar backup**. O LeoBooks valida
tudo antes de trocar qualquer coisa; se algo estiver corrompido, o estado atual
permanece intacto. Backups antigos `.db` continuam aceitos, mas restauram apenas
o banco.

![LeoBooks no tema madrugada](docs/screenshots/tema-escuro.webp)

### No celular

<p align="center">
  <img src="docs/screenshots/mobile.webp" alt="Tela inicial do LeoBooks no celular, com Mariana" width="300">
  <img src="docs/screenshots/mobile-nota.webp" alt="Nova nota no celular, com Mariana" width="300">
</p>

## Dúvidas frequentes

**Onde ficam meus dados?**
No seu servidor. No Docker, no volume `leobooks_instance`; na instalação nativa,
em `/var/lib/leobooks`; rodando com Python, em `instance/`. Não há envio para
uma nuvem do LeoBooks.

**Como atualizo o app?**
No Debian/Fedora, instale o pacote novo e reinicie o serviço. No Docker:

```bash
docker compose pull
docker compose up -d --no-build
```

O volume de dados é preservado.

**Como faço backup?**
Entre como administradora em **Ajustes → Dados e backup → Baixar backup
completo**. Guarde o ZIP fora do servidor. Para restaurar, use o mesmo arquivo
em **Restaurar backup**.

**Esqueci minha senha. E agora?**
Não há recuperação por e-mail. Peça à conta administradora para criar outra
conta, ou remova o volume e comece de novo em um ambiente de testes.

**O app nativo abriu uma janela preta.**
Confira se o serviço está ativo e escutando na 5057:

```bash
systemctl status leobooks --no-pager
curl -i http://127.0.0.1:5057/healthz
```

Se o `curl` não responder, veja os logs:

```bash
sudo journalctl -u leobooks -n 80 --no-pager
```

Em GPUs problemáticas, tente:

```bash
LEOBOOKS_GTK_SAFE=1 leobooks
```

O modo seguro usa o renderizador de software do WebKitGTK.

**O app nativo e o Docker mostram dados diferentes.**
É esperado: são instalações separadas. O app nativo usa `/var/lib/leobooks`; o
Docker usa o volume `leobooks_instance`. Use o backup ZIP para migrar.

**A porta 5059 é o app nativo?**
Não. O Docker publica `5059` no host e escuta `5057` dentro do container. O app
nativo usa `127.0.0.1:5057`. São portas diferentes; uma instalação não bloqueia a
outra.

**Preciso de internet?**
Não para ler e anotar. A internet só é usada quando você pede para buscar capas
em bases públicas.

**Por que apareceu um livro que eu não cadastrei?**
É o livro de exemplo do primeiro acesso. Pode ser excluído em **Biblioteca**.

**Funciona em leitores digitais?**
O caderno é acessado pelo navegador do celular/computador ou pelo aplicativo
GTK no GNOME. Não é um aplicativo nativo para Kindle/Kobo.

## Técnico

<details>
<summary><strong>Stack, segurança, memória, logs, pacotes e desenvolvimento</strong></summary>

### Stack

Flask 3 + SQLite + Jinja + Bootstrap 5 local. Em produção, Waitress no modo
local ou Gunicorn no Docker (1 worker, 4 threads). No Debian/Fedora/Arch, o app
GTK usa GTK 3 + WebKitGTK 4.1 e conversa com o serviço local. Os assets de
interface (Bootstrap, ícones e fontes) são servidos localmente.

### Segurança

- CSRF em todos os formulários e requisições de escrita.
- Markdown convertido e sanitizado contra XSS.
- Senhas com hash Scrypt do Werkzeug.
- Uploads reescritos com Pillow, sem EXIF, servidos por rotas autenticadas.
- Busca de capas com allowlist de hosts, URLs assinadas e limite de tamanho.
- CSP, `X-Content-Type-Options`, `X-Frame-Options` e `Referrer-Policy`.
- Restauração de backup validada e restrita à administradora.
- Dados nativos em `/var/lib/leobooks`, serviço systemd com usuário dedicado e
  `ProtectSystem=strict`.

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

O endpoint `/healthz` é chamado pelo Docker a cada **5 minutos** e é filtrado do
access log. O resultado continua validando banco e HTTP; erros de health
aparecem no log de erro do container.

```bash
docker compose logs -f leobooks
journalctl -u leobooks -f
```

### Variáveis principais

| Variável | Padrão | Para que serve |
| --- | --- | --- |
| `LEOBOOKS_PORT` | `5057` | Porta interna/local. |
| `LEOBOOKS_INSTANCE` | `instance/` no código | Diretório de dados; nos pacotes, `/var/lib/leobooks`. |
| `LEOBOOKS_SAMPLE_BOOK` | `1` | Cria o livro de exemplo em cada cadastro. |
| `LEOBOOKS_COVER_LOOKUP` | `1` | Liga/desliga a busca de capas. |
| `LEOBOOKS_IMAGE_TAG` | `latest` | Tag da imagem `nickolback/leobooks`. |
| `LEOBOOKS_HTTPS` | `0` | Ativa cookies seguros atrás de HTTPS. |
| `LEOBOOKS_LOG_LEVEL` | `INFO` | Nível dos logs. |
| `LEOBOOKS_BACKUP_MAX_BYTES` | `536870912` | Limite do upload de backup (512 MB). |
| `INSTALL_OCR` | `false` | Instala Tesseract na imagem Docker. |

O arquivo [.env.example](.env.example) traz as opções comentadas.

### Pacotes nativos e AppStream

Os pacotes instalam:

- código em `/opt/leobooks`;
- serviço systemd `leobooks.service`;
- app GTK em `/usr/bin/leobooks`;
- configuração em `/etc/leobooks/leobooks.env`;
- dados em `/var/lib/leobooks`;
- atalho e ícone no GNOME;
- metadados AppStream e capturas para o GNOME Software/loja.

Gerar novamente:

```bash
./packaging/build-deb.sh
./packaging/build-rpm.sh   # usa um container Fedora 42
./packaging/build-tarball.sh
```

Os artefatos ficam em `dist/`, com `SHA256SUMS` e `BUILD-INFO.txt`. O RPM é
específico para Fedora 42 x86_64; o `.deb` para Debian 13 amd64. Rebuilde no
alvo para outra versão/arquitetura.

### Docker Hub

```bash
docker login
docker compose build
docker compose push
```

Para uma release versionada:

```bash
LEOBOOKS_IMAGE_TAG=1.0.7 docker compose build
LEOBOOKS_IMAGE_TAG=1.0.7 docker compose push
```

### Testes

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
```

Estado atual: **107 testes passando** — rotas, CSRF, isolamento entre contas,
sanitização de Markdown, uploads, busca de capas, backup, tutorial, cache e
exclusão de conta.

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
packaging/        Debian, RPM, tarball, systemd e AppStream
scripts/          geração das capturas com a conta fictícia Mariana
tests/            suíte de testes
wireframe/        referências originais de design
```

</details>

---

Feito para ler devagar e anotar com intenção.
