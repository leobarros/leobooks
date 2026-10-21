# Skill LeoBooks Development Specialist

Esta skill estabelece o contexto, as diretrizes de código, os padrões de segurança e as especificações de design para o desenvolvimento do aplicativo LeoBooks utilizando Flask (WSGI), SQLite, Bootstrap e Markdown.

1. Contexto & Objetivos

O LeoBooks é uma aplicação web e mobile para captura, organização e consulta de notas, resumos e citações de livros. O foco do sistema é a captura rápida de insights, organização por tags, suporte a rich text/Markdown, revisão diária e gerenciamento de leitura.

2. Requisitos Técnicos & Arquitetura

Stack Tecnológica & Interfaces WSGI

Backend / Interface: Python 3.10+ utilizando Flask com conformidade total à especificação WSGI (Web Server Gateway Interface) para fácil implantação via servidores WSGI (Gunicorn, uWSGI, Waitress).

Formulários WSGI: Processamento seguro de formulários via requisições HTTP POST/GET tratadas pelo WSGI/Flask (WTForms ou manipulação WSGI nativa com validação estrita).

Processamento de Markdown:

Suporte a formatação Markdown para resumos, notas e citações (uso de biblioteca Python como markdown ou mistune).

Sanitização XSS Obrigatória: Todo conteúdo renderizado de Markdown para HTML DEVE obrigatoriamente passar por sanitização contra ataques XSS (utilizando bleach ou equivalente com whitelist restrita de tags e atributos HTML).

Banco de Dados: SQLite (leobooks.db) gerenciado via SQLAlchemy.

Frontend: HTML5, CSS3, JavaScript puro (ES6+).

UI/UX Framework: Bootstrap 5 e Bootstrap Icons (servidos obrigatoriamente de forma LOCAL no diretório /static/vendor/ — sem dependência de CDNs externas).

Testes: Framework unittest ou pytest. Toda alteração no código deve vir acompanhada de testes unitários funcionais (incluindo testes de renderização e sanitização de Markdown).

3. Segurança & Boas Práticas (Security First)

Autenticação & Senhas:

Senhas devem ser armazenadas utilizando algoritmos seguros de hash (ex.: werkzeug.security.generate_password_hash com PBKDF2 ou Scrypt).

Validação de Senha: A senha deve possuir estritamente entre 4 e 10 caracteres.

Proteção de Dados & Input Handling:

Proteção CSRF em todos os formulários WSGI via Flask-WTF / CSRFProtect.

Uso exclusivo de consultas ORM/parametrizadas para impedir SQL Injection.

Sanitização contra XSS: O HTML gerado a partir de entradas Markdown deve ser limpo antes de ser renderizado na view ou marcado como seguro (Markup() / Jinja filter seguro somente após bleach.clean()).

Isolamento de dados: Um usuário autenticado só pode visualizar, editar ou excluir seus próprios dados (livros, notas e tags).

4. Design, UX e Tema (Claro/Escuro)

Responsividade: Layout totalmente adaptável para dispositivos móveis e desktop.

Alternância de Tema (Light/Dark Mode):

Suporte a tema claro e escuro em todas as telas.

Persistência da preferência do tema no perfil do usuário no banco de dados e via localStorage para carregamento instantâneo.

Uso das variáveis CSS do Bootstrap 5 (data-bs-theme="dark" / data-bs-theme="light").

Fidelidade aos Wireframes:

Dashboard/Início: Cards de livros em leitura, progresso, botão proeminente [ + Nova Nota Rápida ] e citação do dia.

Detalhes do Livro: Cabeçalho com capa, metadados e barra de progresso; filtros por tipo de nota (Todas, Citações, Resumos); listagem em cards com Markdown renderizado, tags e páginas.

Modal de Captura Rápida: Formulário WSGI em modal contendo seleção de livro, tipo de nota (rádio), editor/campo de texto com suporte a Markdown, botão de captura via foto/OCR, capítulo, página e gerenciamento de tags.

5. Módulos do Sistema

A. Autenticação & Conta

Login, Cadastro de Conta e Logout.

Regra de validação de senha: mínimo 4 e máximo 10 caracteres.

B. Gestão de Livros, Resumos & Notas (WSGI + Markdown)

CRUD completo de Livros (Título, Autor, Editora, ISBN, Páginas Totais, Página Atual, Status, Capa).

CRUD completo de Notas via formulários WSGI (Tipo: Citação, Resumo, Insight; Conteúdo em Markdown; Capítulo; Página).

Conversão segura do Markdown para HTML com filtro de sanitização contra XSS no backend.

Associação M:N com Tags coloridas.

C. Menu do Usuário & Área Administrativa (/admin ou /settings)

Troca de Senha: Alteração respeitando o limite de 4 a 10 caracteres.

Tema do App: Alternância imediata entre Modo Claro e Modo Escuro.

Backup da Base de Dados: Download direto do arquivo SQLite (leobooks_backup.db).

Restauração de Backup: Upload de arquivo .db via formulário WSGI multipart com validação de integridade.

Exclusão de Conta: Exclusão definitiva da conta e de todos os dados vinculados (Cascade Delete).

6. Diretriz para Criação e Atualização do Código (Workflow)

Para qualquer alteração ou nova funcionalidade solicitada:

Escrever a implementação no arquivo correspondente (app.py, models.py, routes.py, helpers.py, etc.).

Garantir a sanitização: Verificar se o tratamento de formulários WSGI e conversão de Markdown utilizam a política de sanitização XSS.

Criar ou atualizar o arquivo de teste unitário em /tests/ (testando rotas WSGI, sanitização de Markdown e validações).

Garantir que os arquivos estáticos do Bootstrap e Bootstrap Icons permaneçam em /static/vendor/.

7. Estrutura de Diretórios Esperada

leobooks/
├── app.py
├── config.py
├── models.py
├── utils/
│   └── markdown_helper.py  # Módulo de conversão e sanitização XSS
├── database.db
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── app.js
│   └── vendor/
│       ├── bootstrap/
│       │   ├── css/bootstrap.min.css
│       │   └── js/bootstrap.bundle.min.js
│       └── bootstrap-icons/
│           ├── bootstrap-icons.css
│           └── fonts/
├── templates/
│   ├── base.html
│   ├── auth/
│   │   ├── login.html
│   │   └── register.html
│   ├── dashboard.html
│   ├── book_detail.html
│   └── admin.html
└── tests/
    ├── test_auth.py
    ├── test_books.py
    ├── test_markdown_sanitizer.py
    └── test_admin.py
