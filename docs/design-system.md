# LeoBooks — Design System

**Versão:** 1.0  
**Status:** congelado para mudanças visuais não solicitadas  
**Stack visual:** Bootstrap 5.3.8 + Bootstrap Icons 1.13.1, servidos localmente.

Este documento registra o design **atual** do LeoBooks. Ele não propõe um
redesenho: serve como fonte de verdade para manter a estante, o caderno e os
formulários coerentes nos temas claro e madrugada.

> **Regra de mudança visual:** nenhuma alteração de cor, fonte, ícone, espaçamento
> ou componente deve ser aplicada sem antes ser apresentada ao usuário e
> validada em conjunto. Ver “Processo de mudança” no final.

## 1. Princípios

- **Caderno, não dashboard.** Papel, tinta, margens e tipografia editorial antes
  de cards genéricos e excesso de métricas.
- **Leitura primeiro.** A interface deve sumir ao redor do livro, da citação e
  da nota.
- **Calma e intenção.** Contraste quente, poucos acentos e nenhuma competição
  visual entre navegação, conteúdo e ações.
- **Bootstrap como base, não como aparência final.** Componentes e utilitários
  vêm do Bootstrap; a identidade vem dos tokens `--lb-*`.
- **Temas equivalentes.** Claro e madrugada usam a mesma hierarquia e os mesmos
  componentes, com tokens próprios.
- **Tudo local.** Fontes, Bootstrap, ícones e imagens não dependem de CDN.

## 2. Fontes de verdade

| Recurso | Arquivo |
| --- | --- |
| Tokens de cor, tipografia, sombra e layout | `static/css/style.css` (`:root` e `[data-bs-theme="dark"]`) |
| Fontes locais | `static/css/fonts.css` e `static/fonts/` |
| Bootstrap 5.3.8 | `static/vendor/bootstrap/` |
| Bootstrap Icons 1.13.1 | `static/vendor/bootstrap-icons/` |
| Capturas de referência | `docs/screenshots/` |
| Marca | `static/img/logo-leao.svg`, `static/img/favicon.svg` |

## 3. Cores e temas

### 3.1 Tokens semânticos

| Token | Claro | Madrugada | Uso |
| --- | --- | --- | --- |
| `--lb-paper` | `#f2ebdc` | `#131110` | Fundo da página |
| `--lb-paper-soft` | `#f7f1e5` | `#181512` | Fundo secundário |
| `--lb-surface` | `#fffcf5` | `#1d1915` | Cards, campos e superfícies |
| `--lb-surface-2` | `#f6efe1` | `#241f1a` | Superfície alternada |
| `--lb-ink` | `#201c16` | `#f1e8d7` | Texto principal |
| `--lb-ink-2` | `#4d4538` | `#c9bda9` | Texto de apoio |
| `--lb-ink-3` | `#6b6152` | `#a29684` | Texto discreto/metadados |
| `--lb-rule` | `rgba(32,28,22,.15)` | `rgba(241,232,215,.15)` | Bordas e divisores |
| `--lb-rule-soft` | `rgba(32,28,22,.08)` | `rgba(241,232,215,.07)` | Divisores leves |
| `--lb-rule-strong` | `rgba(32,28,22,.30)` | `rgba(241,232,215,.30)` | Bordas de ênfase |
| `--lb-forest` | `#1e4a3c` | `#a8c3a6` | Ação primária, links, navegação |
| `--lb-forest-deep` | `#14352b` | `#0e2620` | Verde profundo |
| `--lb-ochre` | `#a9741f` | `#dfa95a` | Acento editorial |
| `--lb-gold` | `#d6a24a` | `#e6bd76` | Detalhes, foco, destaque |
| `--lb-clay` | `#aa4f37` | `#e18d6d` | Acento terroso e hover |
| `--lb-sage` | `#6d826c` | `#a8bfa4` | Apoio, tags |
| `--lb-plum` | `#6c4356` | `#cb9fb3` | Apoio, tags |
| `--lb-feature-bg` | `#163a30` | `#0f2922` | Bloco de destaque |
| `--lb-feature-ink` | `#f6eedc` | `#f4ecd9` | Texto sobre destaque |
| `--lb-cta-bg` | `#1e4a3c` | `#adc6a9` | Botão principal |
| `--lb-cta-ink` | `#fbf5e7` | `#13221b` | Texto do botão principal |
| `--lb-cta-hover` | `#16392e` | `#c0d6bc` | Hover do botão principal |
| `--lb-danger` | `#a53e2b` | `#e08468` | Erro, exclusão, alerta |

### 3.2 Regras de uso

- Não introduza cores hexadecimais diretamente em templates.
- Use os tokens `--lb-*`; para componentes Bootstrap, use a ponte
  `--bs-*` definida no `:root` e no tema escuro.
- **Floresta** é ação/navegação. **Ocre/dourado** é acento editorial.
  **Terracota** é hover, alerta e calor. **Sálvia/ameixa** são tons de apoio
  para tags.
- O tema madrugada não é uma inversão automática: ele tem tokens próprios para
  manter contraste e a sensação de papel escuro.
- Texto sobre `--lb-feature-bg` usa `--lb-feature-ink`.
- Não use preto puro (`#000`) nem branco puro (`#fff`) como texto/fundo.

### 3.3 Ponte Bootstrap

```css
--bs-body-bg: var(--lb-paper);
--bs-body-color: var(--lb-ink);
--bs-body-font-family: var(--lb-sans);
--bs-border-color: var(--lb-rule);
--bs-primary: var(--lb-forest);
--bs-link-color: var(--lb-forest);
--bs-link-hover-color: var(--lb-clay);
--bs-border-radius: var(--lb-radius);
--bs-box-shadow: var(--lb-shadow-sm);
```

O tema é aplicado em `<html data-bs-theme="light|dark">`, persistido no perfil e
em `localStorage` (`leobooks-theme`). O script `static/js/theme-init.js` evita
flash de tema no primeiro paint.

## 4. Tipografia

| Família | Papel | Pesos | Uso |
| --- | --- | --- | --- |
| **Fraunces** | Display editorial | 300–700, normal/itálico | Títulos, hero, números grandes, citações de destaque |
| **Newsreader** | Leitura | 300–600, normal/itálico | Corpo de notas, Markdown, revisão |
| **Inter** | Interface | 300–700 | Navegação, formulários, botões, metadados |
| **Mono** | Técnico | — | ISBN, página, atalhos, folios |

- Fontes são locais (`static/fonts/`), com `font-display: swap` e subsets
  latin/latin-ext.
- **Fraunces** nunca é usada em textos longos de leitura.
- **Newsreader** é a voz do conteúdo; **Inter** é a voz dos controles.
- Rótulos de seção usam caixa alta, letter-spacing e tamanho pequeno
  (`.lb-eyebrow`).
- Títulos de página usam `clamp(2.85rem, 5.3vw, 4.5rem)` via `.lb-display`.
- Não carregue fontes externas nem troque a família sem validação conjunta.

## 5. Ícones

- Biblioteca: **Bootstrap Icons 1.13.1**, local.
- Uso: `<i class="bi bi-*" aria-hidden="true"></i>` quando o texto ao lado já
  descreve a ação; `aria-label` obrigatório em botões somente com ícone.
- Tamanhos usuais: `0.8–1.16rem`; ícones de botão não devem competir com o
  texto.
- Ícones são lineares e discretos; não use emojis como ícones de interface.
- Ações destrutivas usam `bi-trash`/`bi-x-lg` com confirmação, nunca apenas cor.
- O ícone do produto é o selo do leão; não substitua por ícone genérico.

## 6. Layout, espaçamento e forma

| Token/medida | Valor |
| --- | --- |
| Sidebar | `272px` |
| Largura máxima do conteúdo | `1180px` |
| Gutter | `clamp(20px, 4vw, 62px)` |
| Raio base | `3px` |
| Sombra padrão | `--lb-shadow-sm` / `--lb-shadow` |
| Sombra de capa | `--lb-shadow-cover` |
| Breakpoints principais | `1240px`, `1080px`, `991.98px`, `700px`, `380px` |

- A estante usa capas como âncoras visuais; texto e metadados ficam abaixo.
- Em telas menores, a sidebar dá lugar à barra inferior e ao botão central de
  nova nota.
- O layout é editorial: margens generosas, divisores finos e poucos blocos
  pesados.
- Não use `box-shadow` forte, gradientes chamativos ou cantos muito arredondados
  fora dos tokens.

## 7. Componentes

| Componente | Classes base | Observações |
| --- | --- | --- |
| Botão | `.lb-btn`, `.lb-btn--primary`, `--ghost`, `--quiet`, `--dark`, `--danger`, `--sm`, `--lg` | Altura mínima, ícone e rótulo; não criar botão só com cor |
| Campo | `.lb-input`, `.lb-select`, `.lb-label`, `.lb-input--lg` | Foco visível, placeholder discreto, erro com `--lb-danger` |
| Card de livro | `.lb-bookcard`, `.lb-bookcard__cover`, `__info`, `__badge` | Capa, status, progresso e contagem de notas |
| Linha de leitura | `.lb-bookrow` | Lista compacta no dashboard |
| Nota | `.lb-note`, `.lb-note--quote/summary/insight` | Cor e ícone pelo tipo; Markdown seguro |
| Tag | `.lb-tag` | Cor por tag; `#` como parte visual |
| Status | `.lb-status` | Rótulo + ícone; nunca só cor |
| Progresso | `.lb-progress` | Barra fina e metadados |
| Modal | `.lb-modal` | Captura, busca, confirmação, onboarding |
| Navegação | `.lb-nav`, `.lb-sidebar`, `.lb-mobilebar`, `.lb-bottomnav` | Sidebar desktop; barra inferior móvel |
| Vazio | `.lb-empty` | Instrução curta + ação clara |

Novos componentes devem reutilizar essas classes e os tokens; não criar uma
segunda linguagem visual.

## 8. Estados e acessibilidade

- Foco visível: contorno tracejado em `--lb-clay`; não remova `:focus-visible`.
- Contraste: texto principal sobre papel/superfície deve permanecer legível nos
  dois temas; não use `--lb-ink-3` para texto essencial.
- Status, tags e tipos de nota sempre têm rótulo textual além da cor.
- Botões de ícone precisam de `aria-label`; imagens decorativas usam
  `alt=""`/`aria-hidden="true"`.
- Modais usam Bootstrap com foco e `Esc`; não bloqueie a saída sem intenção.
- `prefers-reduced-motion` já é respeitado no CSS; mantenha animações curtas.
- Teste teclado, tema claro, tema madrugada e viewport móvel.

## 9. O que não fazer

- Não usar CDN para Bootstrap, ícones ou fontes.
- Não alterar arquivos em `static/vendor/` manualmente.
- Não introduzir uma nova paleta, fonte ou família de ícones por conta própria.
- Não trocar `data-bs-theme` por uma solução de tema paralela.
- Não usar estilos inline para cores; exceções dinâmicas (progresso/tag) usam
  variáveis CSS.
- Não redesenhar uma tela “de passagem” durante uma correção funcional.

## 10. Processo de mudança visual

1. **Propor** a mudança: o que muda, por quê, quais tokens/componentes/telas.
2. **Aguardar validação do usuário** antes de implementar. Nenhuma alteração de
   estilo é aplicada sem essa conversa.
3. Implementar preferencialmente via tokens em `static/css/style.css` e classes
   existentes.
4. Validar **tema claro e madrugada**, desktop e mobile, com capturas antes/depois.
5. Rodar a suíte local e validar no Docker, conforme `AGENTS.md`.
6. Atualizar este documento e o `CHANGELOG.md` quando a mudança for aprovada.

Enquanto a pausa de pacotes Linux estiver ativa em `AGENTS.md`, não gerar
`.deb`, `.rpm`, tarball ou releases de pacotes.

## 11. Referências visuais

- [Início — tema claro](screenshots/inicio.webp)
- [Biblioteca](screenshots/biblioteca.webp)
- [Livro e notas](screenshots/livro.webp)
- [Nova nota](screenshots/nota.webp)
- [Tema madrugada](screenshots/tema-escuro.webp)
- [Celular](screenshots/mobile.webp)
