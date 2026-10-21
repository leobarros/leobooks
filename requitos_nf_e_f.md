# Requisitos

Um aplicativo focado em leitura, anotações e estudo de livros exige um equilíbrio entre a facilidade de captura rápida (para não interromper o fluxo de leitura) e a organização estruturada (para facilitar revisões futuras).

---

## Requisitos Funcionais (RF)

Descrevem **o que** o sistema deve fazer e quais funcionalidades devem estar disponíveis para o usuário.

### 1. Gestão de Biblioteca & Livros

* **RF01 - Cadastrar Livro:** Permitir o cadastro manual (Título, Autor, Editora, Número de Páginas, ISBN, Capa) ou busca automática via API externa (ex.: Google Books API / Open Library).
* **RF02 - Status de Leitura:** Classificar o livro por estados (*Quero Ler*, *Lendo*, *Lido*, *Abandonado*).
* **RF03 - Acompanhamento de Progresso:** Registrar a página atual ou porcentagem concluída, calculando automaticamente o ritmo de leitura.

### 2. Gestão de Notas, Resumos e Citações

* **RF04 - Criar Anotações:** Criar notas associadas a um livro específico, permitindo categorização por tipo:
* **Citação (Quote):** Texto literal com a indicação da página/capítulo.
* **Resumo:** Visão geral de um capítulo ou seção em palavras próprias.
* **Insight/Pensamento:** Ideia rápida gerada a partir da leitura.

* **RF05 - Editor de Texto Rico:** Suporte a formatação básica (negrito, itálico, listas) e marcação em **Markdown**.
* **RF06 - Mídia e OCR (Opcional/Avançado):** Permitir anexar fotos da página do livro ou extrair o texto de uma foto via OCR (Reconhecimento Óptico de Caracteres).

### 3. Organização, Busca e Exportação

* **RF07 - Tags e Categorias:** Permitir adicionar tags às notas (ex.: `#filosofia`, `#produtividade`, `#metaficcao`) para vincular ideias de livros diferentes.
* **RF08 - Busca Global:** Pesquisar por palavras-chave no título, autor, conteúdo das notas, citações e tags.
* **RF09 - Exportação de Dados:** Exportar resumos e citações em formatos comuns, como **Markdown (`.md`)**, **PDF** e **JSON**.
* **RF10 - Modos de Revisão (Cards/Flashcards):** Gerar uma visualização aleatória ou diária de citações salvas para revisão de aprendizado.

---

## Requisitos Não Funcionais (RNF)

Descrevem **como** o sistema deve operar, focando em qualidade, desempenho e arquitetura.

### 1. Usabilidade e Experiência (UX/UI)

* **RNF01 - Captura Rápida:** A interface para adicionar uma citação ou nota rápida deve exigir no máximo 3 toques/cliques a partir da tela inicial.
* **RNF02 - Suporte a Modo Escuro (Dark Mode):** Interface adaptável para leitura e anotação em ambientes com pouca iluminação.

### 2. Desempenho e Disponibilidade

* **RNF03 - Arquitetura Offline-First:** O app deve permitir leitura, busca e criação de notas sem conexão com a internet, sincronizando os dados em segundo plano quando houver rede.
* **RNF04 - Tempo de Resposta:** A busca local por notas e citações deve retornar resultados em menos de 200 milissegundos.

### 3. Portabilidade e Armazenamento

* **RNF05 - Sincronização e Backup:** Permitir sincronização segura dos dados entre múltiplos dispositivos ou backup em nuvem (ex.: armazenando localmente em banco relacional SQLite e sincronizando via API/Cloud Storage).
* **RNF06 - Exportação Livre de Lock-in:** Garantir que o banco de dados e os arquivos salvos não fiquem presos em formato proprietário, mantendo o padrão aberto (Markdown/JSON).
