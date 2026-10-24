/* ==========================================================================
   LeoBooks — interações (JavaScript puro, sem dependências além do Bootstrap)
   --------------------------------------------------------------------------
   • tema claro/escuro (localStorage + perfil no servidor)
   • modal de captura rápida e edição de nota
   • editor Markdown com pré-visualização segura e atalhos
   • tags em chips, OCR opcional e prévia da foto
   • compartilhar citação como imagem (Canvas)
   • confirmações, atalhos e avisos
   ========================================================================== */
(function () {
  "use strict";

  const root = document.documentElement;
  const body = document.body;
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const isAuthenticated = body?.dataset.authenticated === "1";
  const themeUrl = body?.dataset.themeUrl || "";
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const $ = (selector, scope = document) => scope.querySelector(selector);
  const $$ = (selector, scope = document) => Array.from(scope.querySelectorAll(selector));

  /* ----------------------------------------------------------------------
     Avisos
     ---------------------------------------------------------------------- */
  const toastHost = $("#lb-toasts");

  function notify(message, variant = "success") {
    if (!toastHost || !message) return;
    const icons = {
      success: "bi-check2",
      danger: "bi-exclamation-octagon",
      warning: "bi-exclamation-triangle",
      info: "bi-info-lg",
    };
    const el = document.createElement("div");
    el.className = `lb-flash lb-flash--${variant}`;
    el.setAttribute("role", "status");
    el.innerHTML = `
      <span class="lb-flash__icon"><i class="bi ${icons[variant] || icons.info}"></i></span>
      <span class="lb-flash__text"></span>
      <button type="button" class="lb-flash__close" aria-label="Fechar aviso"><i class="bi bi-x-lg"></i></button>`;
    el.querySelector(".lb-flash__text").textContent = message;
    toastHost.appendChild(el);
    el.querySelector(".lb-flash__close").addEventListener("click", () => removeFlash(el));
    window.setTimeout(() => removeFlash(el), 3800);
  }

  function removeFlash(el) {
    if (!el || el.classList.contains("is-leaving")) return;
    el.classList.add("is-leaving");
    window.setTimeout(() => el.remove(), 240);
  }

  $$("[data-flash]").forEach((flash) => {
    const close = $("[data-dismiss-flash]", flash);
    close?.addEventListener("click", () => removeFlash(flash));
    const timeout = flash.classList.contains("lb-flash--danger") ? 8000 : 4500;
    window.setTimeout(() => removeFlash(flash), timeout);
  });

  /* ----------------------------------------------------------------------
     Tema
     ---------------------------------------------------------------------- */
  function applyTheme(theme, persistLocally = true) {
    if (theme !== "light" && theme !== "dark") return;
    root.setAttribute("data-bs-theme", theme);
    if (persistLocally) {
      try {
        localStorage.setItem("leobooks-theme", theme);
      } catch (error) {
        /* armazenamento indisponível */
      }
    }
    const meta = $('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", theme === "dark" ? "#141210" : "#F3ECDD");
    $$("[data-theme-toggle]").forEach((button) => {
      button.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
    });
    $$("[data-theme-choice]").forEach((choice) => {
      const active = choice.dataset.themeChoice === theme;
      choice.classList.toggle("is-active", active);
      choice.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function persistTheme(theme) {
    if (!isAuthenticated || !themeUrl) return;
    fetch(themeUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
        "X-Requested-With": "fetch",
        Accept: "application/json",
      },
      body: JSON.stringify({ theme }),
    }).catch(() => {
      /* O tema local continua válido mesmo sem rede. */
    });
  }

  $$("[data-theme-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const next = root.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
      applyTheme(next);
      persistTheme(next);
    });
  });

  $$("[data-theme-choice]").forEach((choice) => {
    choice.addEventListener("click", (event) => {
      event.preventDefault();
      const theme = choice.dataset.themeChoice;
      applyTheme(theme);
      persistTheme(theme);
      notify(theme === "dark" ? "Tema madrugada ativado." : "Tema papel ativado.", "success");
    });
  });

  applyTheme(root.getAttribute("data-bs-theme") === "dark" ? "dark" : "light", false);

  /* ----------------------------------------------------------------------
     Bootstrap helpers
     ---------------------------------------------------------------------- */
  const modal = (element) => (element && window.bootstrap ? window.bootstrap.Modal.getOrCreateInstance(element) : null);
  const noteModal = $("#noteModal");
  const noteModalInstance = modal(noteModal);
  const searchModal = $("#searchModal");
  const searchModalInstance = modal(searchModal);
  const confirmModalEl = $("#confirmModal");
  const confirmModalInstance = modal(confirmModalEl);

  /* ----------------------------------------------------------------------
     Formulários com confirmação
     ---------------------------------------------------------------------- */
  let pendingForm = null;

  $$("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (form.dataset.confirmed === "1" || !confirmModalInstance) return;
      event.preventDefault();
      pendingForm = form;
      const message = $("#confirmMessage");
      const accept = $("#confirmAccept");
      if (message) message.textContent = form.dataset.confirm || "Esta ação não pode ser desfeita.";
      if (accept) accept.textContent = form.dataset.confirmLabel || "Sim, continuar";
      confirmModalInstance.show();
    });
  });

  $("#confirmAccept")?.addEventListener("click", () => {
    if (!pendingForm) return;
    const form = pendingForm;
    pendingForm = null;
    form.dataset.confirmed = "1";
    confirmModalInstance?.hide();
    if (typeof form.requestSubmit === "function") {
      form.removeAttribute("data-confirm");
      form.requestSubmit();
    } else {
      form.submit();
    }
  });

  confirmModalEl?.addEventListener("hidden.bs.modal", () => {
    pendingForm = null;
  });

  /* ----------------------------------------------------------------------
     Auto-submit (filtros e status)
     ---------------------------------------------------------------------- */
  $$("[data-auto-submit]").forEach((select) => {
    select.addEventListener("change", () => {
      const form = select.form;
      if (!form) return;
      if (typeof form.requestSubmit === "function") form.requestSubmit();
      else form.submit();
    });
  });

  /* ----------------------------------------------------------------------
     Progresso do digital e formato do livro
     ---------------------------------------------------------------------- */
  const progressForm = $("[data-progress-form]");
  if (progressForm) {
    const totalPages = Number(progressForm.dataset.totalPages || 0);
    const percentInput = $("#currentPercent", progressForm);
    const percentEquivalent = $("[data-progress-equivalent]", progressForm);

    const updatePercentEquivalent = () => {
      if (!percentInput || !percentEquivalent) return;
      if (!totalPages) {
        percentEquivalent.textContent = "percentual do livro digital";
        return;
      }
      const raw = parseFloat(percentInput.value);
      if (!Number.isFinite(raw)) {
        percentEquivalent.textContent = "informe o percentual";
        return;
      }
      const percent = Math.max(0, Math.min(100, raw));
      const page = Math.round((totalPages * percent) / 100);
      percentEquivalent.textContent = `≈ página ${page} de ${totalPages}`;
    };

    percentInput?.addEventListener("input", updatePercentEquivalent);
    updatePercentEquivalent();
  }

  const bookMediaForm = $("[data-book-media-form]");
  if (bookMediaForm) {
    const mediaInputs = $$('input[name="media_type"]', bookMediaForm);
    const mediaPanels = $$("[data-media-panel]", bookMediaForm);
    const currentPageInput = $("#current_page", bookMediaForm);
    const currentPercentInput = $("#current_percent", bookMediaForm);
    const totalPagesInput = $("#total_pages", bookMediaForm);
    const requiredStar = $("[data-media-required]", bookMediaForm);
    const totalHint = $("[data-media-total-hint]", bookMediaForm);

    const syncBookMedia = () => {
      const selected = mediaInputs.find((input) => input.checked)?.value || "PHYSICAL";
      const isDigital = selected === "DIGITAL";
      mediaPanels.forEach((panel) => {
        panel.hidden = panel.dataset.mediaPanel !== selected;
      });
      if (currentPageInput) {
        currentPageInput.disabled = isDigital;
        currentPageInput.required = !isDigital;
      }
      if (currentPercentInput) {
        currentPercentInput.disabled = !isDigital;
      }
      if (totalPagesInput) {
        totalPagesInput.required = !isDigital;
      }
      if (requiredStar) requiredStar.hidden = isDigital;
      if (totalHint) totalHint.hidden = !isDigital;
    };

    mediaInputs.forEach((input) => input.addEventListener("change", syncBookMedia));
    syncBookMedia();
  }

  /* ----------------------------------------------------------------------
     Mostrar/ocultar senha
     ---------------------------------------------------------------------- */
  $$("[data-password-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = button.parentElement?.querySelector("input");
      if (!input) return;
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      button.setAttribute("aria-label", showing ? "Mostrar senha" : "Ocultar senha");
      const icon = $("i", button);
      if (icon) icon.className = showing ? "bi bi-eye" : "bi bi-eye-slash";
    });
  });

  /* ----------------------------------------------------------------------
     Pré-visualização segura de Markdown
     ---------------------------------------------------------------------- */
  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function inlineMarkdown(text) {
    let html = text;
    html = html.replace(/`([^`\n]+)`/g, "<code>$1</code>");
    html = html.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/__([^_\n]+)__/g, "<strong>$1</strong>");
    html = html.replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>");
    html = html.replace(/(^|[^_])_([^_\n]+)_/g, "$1<em>$2</em>");
    html = html.replace(/~~([^~\n]+)~~/g, "<s>$1</s>");
    html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    return html;
  }

  function renderMarkdown(source) {
    const lines = escapeHtml(source || "").replace(/\r\n/g, "\n").split("\n");
    const blocks = [];
    let paragraph = [];
    let listType = null;
    let inCode = false;
    let codeLines = [];

    const flushParagraph = () => {
      if (paragraph.length) {
        blocks.push(`<p>${inlineMarkdown(paragraph.join("<br>"))}</p>`);
        paragraph = [];
      }
    };
    const closeList = () => {
      if (listType) {
        blocks.push(`</${listType}>`);
        listType = null;
      }
    };

    lines.forEach((rawLine) => {
      const line = rawLine.trim();

      if (line.startsWith("```")) {
        flushParagraph();
        closeList();
        if (inCode) {
          blocks.push(`<pre><code>${codeLines.join("\n")}</code></pre>`);
          codeLines = [];
          inCode = false;
        } else {
          inCode = true;
        }
        return;
      }
      if (inCode) {
        codeLines.push(rawLine);
        return;
      }
      if (!line) {
        flushParagraph();
        closeList();
        return;
      }

      const heading = line.match(/^(#{1,4})\s+(.*)$/);
      if (heading) {
        flushParagraph();
        closeList();
        const level = heading[1].length;
        blocks.push(`<h${level}>${inlineMarkdown(heading[2])}</h${level}>`);
        return;
      }
      if (/^(-{3,}|\*{3,})$/.test(line)) {
        flushParagraph();
        closeList();
        blocks.push("<hr>");
        return;
      }
      if (/^>\s?/.test(line)) {
        flushParagraph();
        closeList();
        blocks.push(`<blockquote><p>${inlineMarkdown(line.replace(/^>\s?/, ""))}</p></blockquote>`);
        return;
      }
      const unordered = line.match(/^[-*+]\s+(.*)$/);
      if (unordered) {
        flushParagraph();
        if (listType !== "ul") {
          closeList();
          blocks.push("<ul>");
          listType = "ul";
        }
        blocks.push(`<li>${inlineMarkdown(unordered[1])}</li>`);
        return;
      }
      const ordered = line.match(/^\d+[.)]\s+(.*)$/);
      if (ordered) {
        flushParagraph();
        if (listType !== "ol") {
          closeList();
          blocks.push("<ol>");
          listType = "ol";
        }
        blocks.push(`<li>${inlineMarkdown(ordered[1])}</li>`);
        return;
      }

      closeList();
      paragraph.push(line);
    });

    if (inCode && codeLines.length) blocks.push(`<pre><code>${codeLines.join("\n")}</code></pre>`);
    flushParagraph();
    closeList();
    return blocks.join("\n");
  }

  /* ----------------------------------------------------------------------
     Editor de nota / modal de captura
     ---------------------------------------------------------------------- */
  const noteForm = $("#noteForm");
  const editorInput = $("#noteContent");
  const editorPreview = $("[data-editor-preview]");
  const editorCounter = $("[data-editor-counter]");
  const ocrTrigger = $("[data-ocr-trigger]");
  const ocrUrl = ocrTrigger?.dataset.ocrUrl || "";
  const ocrEnabled = ocrTrigger?.dataset.ocrAvailable === "1";
  const photoInput = $("[data-ocr-input]");
  const photoPreview = $("[data-photo-preview]");
  const ocrStatus = $("[data-ocr-status]");
  const tagHidden = $("[data-tag-hidden]");
  const tagInput = $("[data-tag-input]");
  const tagChips = $("[data-tag-chips]");
  let photoObjectUrl = null;

  function updateCounter() {
    if (editorCounter && editorInput) editorCounter.textContent = String(editorInput.value.length);
  }

  function updatePreview() {
    if (!editorPreview || !editorInput) return;
    editorPreview.innerHTML = renderMarkdown(editorInput.value);
  }

  function activeEditorTab() {
    return $("[data-editor-tab].is-active")?.dataset.editorTab || "write";
  }

  function showEditorTab(tab) {
    $$("[data-editor-tab]").forEach((button) => {
      const active = button.dataset.editorTab === tab;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-selected", active ? "true" : "false");
    });
    if (tab === "preview") {
      updatePreview();
      if (editorInput) editorInput.hidden = true;
      if (editorPreview) editorPreview.hidden = false;
    } else {
      if (editorInput) editorInput.hidden = false;
      if (editorPreview) editorPreview.hidden = true;
    }
  }

  $$("[data-editor-tab]").forEach((button) => {
    button.addEventListener("click", () => showEditorTab(button.dataset.editorTab));
  });

  editorInput?.addEventListener("input", () => {
    updateCounter();
    if (activeEditorTab() === "preview") updatePreview();
    editorInput.style.height = "auto";
    editorInput.style.height = `${Math.max(158, editorInput.scrollHeight)}px`;
  });

  function replaceSelection(before, after, placeholder) {
    if (!editorInput) return;
    const start = editorInput.selectionStart;
    const end = editorInput.selectionEnd;
    const selected = editorInput.value.slice(start, end) || placeholder || "";
    const text = before + selected + after;
    editorInput.setRangeText(text, start, end, "end");
    if (!editorInput.value.slice(start, end) && placeholder) {
      editorInput.setSelectionRange(start + before.length, start + before.length + placeholder.length);
    }
    editorInput.focus();
    updateCounter();
    if (activeEditorTab() === "preview") updatePreview();
  }

  function prefixLines(prefix) {
    if (!editorInput) return;
    const start = editorInput.selectionStart;
    const end = editorInput.selectionEnd;
    const value = editorInput.value;
    const lineStart = value.lastIndexOf("\n", start - 1) + 1;
    const lineEnd = end;
    const block = value.slice(lineStart, lineEnd);
    const next = block
      .split("\n")
      .map((line) => (line.trim() ? prefix + line : line))
      .join("\n");
    editorInput.setRangeText(next, lineStart, lineEnd, "select");
    editorInput.focus();
    updateCounter();
  }

  $$("[data-md]").forEach((button) => {
    button.addEventListener("click", () => {
      if (!editorInput) return;
      switch (button.dataset.md) {
        case "bold":
          replaceSelection("**", "**", "texto em negrito");
          break;
        case "italic":
          replaceSelection("*", "*", "texto em itálico");
          break;
        case "quote":
          prefixLines("> ");
          break;
        case "list":
          prefixLines("- ");
          break;
        case "heading":
          prefixLines("## ");
          break;
        case "link":
          replaceSelection("[", "](https://)", "texto do link");
          break;
        case "clear":
          editorInput.value = editorInput.value
            .replace(/\*\*([^*]+)\*\*/g, "$1")
            .replace(/\*([^*]+)\*/g, "$1")
            .replace(/^#{1,6}\s+/gm, "")
            .replace(/^>\s+/gm, "")
            .replace(/^[-*+]\s+/gm, "");
          updateCounter();
          if (activeEditorTab() === "preview") updatePreview();
          break;
        default:
          break;
      }
    });
  });

  editorInput?.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "b") {
      event.preventDefault();
      replaceSelection("**", "**", "texto em negrito");
    }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "i") {
      event.preventDefault();
      replaceSelection("*", "*", "texto em itálico");
    }
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter" && noteForm) {
      event.preventDefault();
      if (typeof noteForm.requestSubmit === "function") noteForm.requestSubmit();
    }
  });

  /* --------------------------- Tags em chips --------------------------- */
  function readTagValues() {
    if (!tagHidden) return [];
    return tagHidden.value
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean);
  }

  function writeTagValues(values) {
    if (!tagHidden) return;
    const unique = [];
    const seen = new Set();
    values.forEach((value) => {
      const clean = value.replace(/^#/, "").replace(/,/g, "").trim().slice(0, 40);
      const key = clean.toLowerCase();
      if (clean && !seen.has(key) && unique.length < 8) {
        seen.add(key);
        unique.push(clean);
      }
    });
    tagHidden.value = unique.join(", ");
    renderTagChips(unique);
  }

  function renderTagChips(values) {
    if (!tagChips) return;
    tagChips.innerHTML = "";
    values.forEach((name) => {
      const chip = document.createElement("span");
      chip.className = "lb-tagedit";
      const label = document.createElement("span");
      label.textContent = `#${name}`;
      const remove = document.createElement("button");
      remove.type = "button";
      remove.setAttribute("aria-label", `Remover tag ${name}`);
      remove.innerHTML = '<i class="bi bi-x"></i>';
      remove.addEventListener("click", () => {
        writeTagValues(readTagValues().filter((value) => value.toLowerCase() !== name.toLowerCase()));
      });
      chip.append(label, remove);
      tagChips.appendChild(chip);
    });
  }

  function addTag(raw) {
    const clean = String(raw || "").replace(/^#/, "").trim();
    if (!clean) return;
    const values = readTagValues();
    if (values.length >= 8) {
      notify("Máximo de 8 tags por nota.", "warning");
      return;
    }
    if (!values.some((value) => value.toLowerCase() === clean.toLowerCase())) {
      values.push(clean);
      writeTagValues(values);
    }
    if (tagInput) tagInput.value = "";
  }

  tagInput?.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      addTag(tagInput.value);
    } else if (event.key === "Backspace" && !tagInput.value) {
      const values = readTagValues();
      values.pop();
      writeTagValues(values);
    }
  });

  tagInput?.addEventListener("blur", () => {
    if (tagInput.value.trim()) addTag(tagInput.value);
  });

  $$("[data-suggestion]").forEach((button) => {
    button.addEventListener("click", () => addTag(button.dataset.suggestion));
  });

  /* --------------------------- Foto / OCR ------------------------------ */
  function clearPhoto() {
    if (photoInput) photoInput.value = "";
    if (photoPreview) photoPreview.hidden = true;
    if (photoObjectUrl) {
      URL.revokeObjectURL(photoObjectUrl);
      photoObjectUrl = null;
    }
    const image = $("[data-photo-image]");
    if (image) image.removeAttribute("src");
  }

  function setOcrStatus(message, state = "") {
    if (!ocrStatus) return;
    ocrStatus.textContent = message;
    ocrStatus.classList.remove("is-busy", "is-error", "is-ok");
    if (state) ocrStatus.classList.add(`is-${state}`);
  }

  $("[data-ocr-trigger]")?.addEventListener("click", () => photoInput?.click());

  photoInput?.addEventListener("change", async () => {
    const file = photoInput.files && photoInput.files[0];
    if (!file) return;
    if (photoObjectUrl) URL.revokeObjectURL(photoObjectUrl);
    photoObjectUrl = URL.createObjectURL(file);
    const image = $("[data-photo-image]");
    const name = $("[data-photo-name]");
    if (image) image.src = photoObjectUrl;
    if (name) name.textContent = file.name;
    if (photoPreview) photoPreview.hidden = false;

    if (!ocrUrl || !ocrEnabled) {
      setOcrStatus("OCR não instalado neste servidor — a foto será anexada à nota.", "error");
      return;
    }
    setOcrStatus("Lendo a página… isso pode levar alguns segundos.", "busy");

    const data = new FormData();
    data.append("photo", file);
    try {
      const response = await fetch(ocrUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-CSRFToken": csrfToken, "X-Requested-With": "fetch" },
        body: data,
      });
      const payload = await response.json().catch(() => ({}));
      if (response.ok && payload.ok && payload.text) {
        const text = payload.text.trim();
        if (editorInput) {
          const prefix = editorInput.value.trim() ? "\n\n" : "";
          editorInput.value = `${editorInput.value}${prefix}${text}`;
        }
        updateCounter();
        updatePreview();
        setOcrStatus("Texto extraído. Revise antes de guardar.", "ok");
        showEditorTab("write");
        editorInput?.focus();
      } else if (payload.reason === "ocr_unavailable") {
        setOcrStatus("OCR não instalado neste servidor — a foto será anexada à nota.", "error");
      } else {
        setOcrStatus(payload.message || "Não consegui ler a imagem. Digite o trecho manualmente.", "error");
      }
    } catch (error) {
      setOcrStatus("Falha de rede ao processar a foto. A imagem segue anexada.", "error");
    }
  });

  $("[data-photo-remove]")?.addEventListener("click", clearPhoto);

  /* --------------------------- Abrir / editar -------------------------- */
  function setNoteMode(mode) {
    const title = $("[data-note-title]");
    const eyebrow = $("[data-note-eyebrow]");
    const submitLabel = $("[data-note-submit] span");
    if (mode === "edit") {
      if (title) title.textContent = "Editar nota";
      if (eyebrow) eyebrow.textContent = "Revisitando uma margem";
      if (submitLabel) submitLabel.textContent = "Salvar alterações";
    } else {
      if (title) title.textContent = noteForm?.dataset.createTitle || "Nova nota";
      if (eyebrow) eyebrow.textContent = noteForm?.dataset.createEyebrow || "Captura rápida";
      if (submitLabel) submitLabel.textContent = "Salvar";
    }
  }

  function resetNoteForm() {
    if (!noteForm) return;
    noteForm.action = noteForm.dataset.createAction || noteForm.action;
    setNoteMode("create");

    $$('input[name="type"]', noteForm).forEach((input) => {
      input.checked = input.value === "QUOTE";
    });
    if (editorInput) editorInput.value = "";
    const chapter = $("#noteChapter", noteForm);
    const page = $("#notePage", noteForm);
    if (chapter) chapter.value = "";
    if (page) page.value = "";
    writeTagValues([]);
    clearPhoto();
    setOcrStatus(
      $("[data-ocr-status]")?.dataset.defaultText || "",
      ""
    );
    updateCounter();
    showEditorTab("write");
  }

  function openNoteModal(options = {}) {
    if (!noteModalInstance || !noteForm) return;
    if (options.reset !== false) resetNoteForm();
    if (options.bookId) {
      const bookSelect = $("#noteBook", noteForm);
      if (bookSelect) bookSelect.value = options.bookId;
    }
    if (options.type) {
      const typeInput = $(`input[name="type"][value="${options.type}"]`, noteForm);
      if (typeInput) typeInput.checked = true;
    }
    noteModalInstance.show();
    window.setTimeout(() => {
      if (options.focus === "photo") {
        $("[data-ocr-trigger]")?.focus();
      } else {
        editorInput?.focus();
        if (editorInput) editorInput.selectionStart = editorInput.value.length;
      }
    }, 320);
  }

  $$("[data-note-open]").forEach((button) => {
    button.addEventListener("click", () => {
      openNoteModal({
        bookId: button.dataset.bookId || "",
        type: button.dataset.noteType || "QUOTE",
        focus: button.dataset.noteFocus || "content",
      });
    });
  });

  $$(".js-edit-note").forEach((button) => {
    button.addEventListener("click", () => {
      if (!noteForm) return;
      resetNoteForm();
      noteForm.action = button.dataset.noteAction;
      setNoteMode("edit");
      const bookSelect = $("#noteBook", noteForm);
      if (bookSelect && button.dataset.noteBook) bookSelect.value = button.dataset.noteBook;
      const typeInput = $(`input[name="type"][value="${button.dataset.noteType}"]`, noteForm);
      if (typeInput) typeInput.checked = true;
      if (editorInput) editorInput.value = button.dataset.noteContent || "";
      const chapter = $("#noteChapter", noteForm);
      const page = $("#notePage", noteForm);
      if (chapter) chapter.value = button.dataset.noteChapter || "";
      if (page) page.value = button.dataset.notePage || "";
      writeTagValues((button.dataset.noteTags || "").split(","));
      updateCounter();
      updatePreview();
      noteModalInstance?.show();
      window.setTimeout(() => {
        editorInput?.focus();
        if (editorInput) editorInput.selectionStart = editorInput.value.length;
      }, 320);
    });
  });

  noteModal?.addEventListener("hidden.bs.modal", () => {
    if (noteForm) {
      noteForm.action = noteForm.dataset.createAction || noteForm.action;
    }
  });

  /* ----------------------------------------------------------------------
     Busca global
     ---------------------------------------------------------------------- */
  $$("[data-search-open]").forEach((button) => {
    button.addEventListener("click", () => {
      if (!searchModalInstance) return;
      searchModalInstance.show();
      window.setTimeout(() => $("[data-search-input]")?.focus(), 320);
    });
  });

  /* ----------------------------------------------------------------------
     Atalhos de teclado
     ---------------------------------------------------------------------- */
  function isTyping(target) {
    if (!target) return false;
    const tag = target.tagName.toLowerCase();
    return tag === "input" || tag === "textarea" || tag === "select" || target.isContentEditable;
  }

  document.addEventListener("keydown", (event) => {
    const openModal = $(".modal.show");
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      if (!openModal) {
        searchModalInstance?.show();
        window.setTimeout(() => $("[data-search-input]")?.focus(), 300);
      }
      return;
    }
    if (event.key.toLowerCase() === "n" && !event.ctrlKey && !event.metaKey && !event.altKey) {
      if (isTyping(event.target) || openModal || !noteForm) return;
      event.preventDefault();
      openNoteModal({ type: "QUOTE" });
    }
  });

  /* ----------------------------------------------------------------------
     Nome do arquivo de backup
     ---------------------------------------------------------------------- */
  $$("[data-file-input]").forEach((input) => {
    input.addEventListener("change", () => {
      const name = input.closest(".lb-filelabel")?.querySelector("[data-file-name]");
      if (!name) return;
      const file = input.files && input.files[0];
      name.textContent = file ? file.name : "Nenhum arquivo escolhido";
      name.classList.toggle("is-empty", !file);
    });
  });

  /* ----------------------------------------------------------------------
     Prévia da capa no formulário de livro
     ---------------------------------------------------------------------- */
  const coverInput = $("#cover");
  const coverPreviewImage = $("[data-cover-preview-image]");
  const coverPreviewRoot = $("[data-cover-preview]");
  const coverLookupWidget = $("[data-cover-lookup-widget]");
  const coverLookupButton = $("[data-cover-lookup]");
  const coverLookupLabel = $("[data-cover-lookup-label]");
  const coverLookupResults = $("[data-cover-results]");
  const coverCandidateInput = $("[data-cover-candidate]");
  const coverSelectedBox = $("[data-cover-selected]");
  const coverSelectedText = $("[data-cover-selected-text]");
  const coverStatus = $("[data-cover-status]");
  let coverBlobUrl = null;

  function originalCoverElements() {
    return $$(".lb-cover, .lb-cover-preview__empty", coverPreviewRoot || document);
  }

  function setCoverStatus(message, state = "") {
    if (!coverStatus) return;
    coverStatus.textContent = message || "";
    coverStatus.classList.remove("is-ok", "is-error", "is-busy");
    if (state) coverStatus.classList.add(`is-${state}`);
  }

  function hideOriginalCover() {
    originalCoverElements().forEach((element) => {
      element.style.display = "none";
    });
  }

  function restoreOriginalCover() {
    originalCoverElements().forEach((element) => {
      element.style.display = "";
    });
  }

  function clearCoverSelection({ restore = true } = {}) {
    if (coverCandidateInput) coverCandidateInput.value = "";
    if (coverSelectedBox) coverSelectedBox.hidden = true;
    if (coverSelectedText) coverSelectedText.textContent = "";
    $$(".lb-coverhit.is-selected").forEach((element) => element.classList.remove("is-selected"));
    if (coverPreviewImage) {
      coverPreviewImage.hidden = true;
      coverPreviewImage.removeAttribute("src");
    }
    if (restore) {
      restoreOriginalCover();
      setCoverStatus("", "");
    }
  }

  function useCoverPreview(src) {
    if (!coverPreviewImage || !src) return;
    coverPreviewImage.src = src;
    coverPreviewImage.hidden = false;
    coverPreviewImage.referrerPolicy = "no-referrer";
    hideOriginalCover();
  }

  function selectCoverCandidate(candidate, button) {
    if (!coverCandidateInput || !candidate || !candidate.token) return;
    if (coverInput) coverInput.value = "";
    if (coverBlobUrl) {
      URL.revokeObjectURL(coverBlobUrl);
      coverBlobUrl = null;
    }
    clearCoverSelection({ restore: false });
    coverCandidateInput.value = candidate.token;
    $$(".lb-coverhit").forEach((element) => element.classList.remove("is-selected"));
    button.classList.add("is-selected");
    useCoverPreview(candidate.preview);
    if (coverSelectedBox) coverSelectedBox.hidden = false;
    if (coverSelectedText) {
      const source = candidate.source || "base pública";
      const title = candidate.title ? ` · ${candidate.title}` : "";
      coverSelectedText.textContent = `${source}${title}`;
    }
    setCoverStatus("Capa escolhida. Ela será baixada e guardada no servidor ao salvar.", "ok");
  }

  function renderCoverResults(candidates) {
    if (!coverLookupResults) return;
    coverLookupResults.innerHTML = "";
    if (!candidates.length) {
      coverLookupResults.hidden = true;
      return;
    }

    candidates.forEach((candidate) => {
      if (!candidate || !candidate.preview || !candidate.token) return;
      const card = document.createElement("button");
      card.type = "button";
      card.className = "lb-coverhit";
      card.setAttribute(
        "aria-label",
        `Usar capa de ${candidate.title || "livro"} — ${candidate.source || "base pública"}`
      );

      const image = document.createElement("img");
      image.src = candidate.preview;
      image.alt = candidate.title ? `Capa de ${candidate.title}` : "Capa do livro";
      image.loading = "lazy";
      image.referrerPolicy = "no-referrer";
      image.addEventListener("error", () => {
        card.disabled = true;
        card.classList.add("is-unavailable");
        image.alt = "Capa indisponível";
      });

      const source = document.createElement("span");
      source.className = "lb-coverhit__source";
      source.textContent = candidate.source || "Base pública";

      const title = document.createElement("span");
      title.className = "lb-coverhit__title";
      title.textContent = candidate.title || "Sem título";

      card.append(image, source, title);
      card.addEventListener("click", () => selectCoverCandidate(candidate, card));
      coverLookupResults.appendChild(card);
    });

    coverLookupResults.hidden = false;
  }

  async function lookupCovers() {
    if (!coverLookupWidget || !coverLookupButton) return;
    const isbnField = $("#isbn");
    const titleField = $("#title");
    const authorsField = $("#authors");
    const isbn = isbnField ? isbnField.value.trim() : "";
    const title = titleField ? titleField.value.trim() : "";
    const authors = authorsField ? authorsField.value.trim() : "";

    if (!isbn && !title) {
      setCoverStatus("Preencha o ISBN ou o título antes de buscar capas.", "error");
      return;
    }

    const url = coverLookupWidget.dataset.url;
    if (!url) return;

    if (coverLookupResults) {
      coverLookupResults.innerHTML = "";
      coverLookupResults.hidden = true;
    }

    coverLookupButton.disabled = true;
    coverLookupButton.classList.add("is-loading");
    if (coverLookupLabel) coverLookupLabel.textContent = "Buscando…";
    setCoverStatus("Consultando Open Library e Google Books…", "busy");

    const data = new FormData();
    data.append("isbn", isbn);
    data.append("title", title);
    data.append("authors", authors);

    try {
      const response = await fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": csrfToken,
          "X-Requested-With": "fetch",
          Accept: "application/json",
        },
        body: data,
      });
      const payload = await response.json().catch(() => ({}));

      if (!response.ok || !payload.ok) {
        setCoverStatus(
          payload.message || "Não foi possível buscar capas agora. Tente novamente.",
          "error"
        );
        return;
      }

      const candidates = Array.isArray(payload.candidates) ? payload.candidates : [];
      renderCoverResults(candidates);
      if (!candidates.length) {
        setCoverStatus(payload.message || "Nenhuma capa encontrada.", "");
        return;
      }
      setCoverStatus(
        payload.message || `${candidates.length} capas encontradas. Escolha uma.`,
        "ok"
      );
    } catch (error) {
      setCoverStatus(
        "Falha de rede ao consultar as bases de capas. Verifique a conexão do servidor.",
        "error"
      );
    } finally {
      coverLookupButton.disabled = false;
      coverLookupButton.classList.remove("is-loading");
      if (coverLookupLabel) coverLookupLabel.textContent = "Buscar capas";
    }
  }

  coverLookupButton?.addEventListener("click", lookupCovers);

  $("[data-cover-clear]")?.addEventListener("click", () => {
    clearCoverSelection();
    if (coverLookupResults) {
      $$(".lb-coverhit", coverLookupResults).forEach((element) => element.classList.remove("is-selected"));
    }
  });

  coverInput?.addEventListener("change", () => {
    const file = coverInput.files && coverInput.files[0];
    if (!file) return;

    if (coverCandidateInput) coverCandidateInput.value = "";
    if (coverSelectedBox) coverSelectedBox.hidden = true;
    $$(".lb-coverhit").forEach((element) => element.classList.remove("is-selected"));
    if (coverBlobUrl) URL.revokeObjectURL(coverBlobUrl);

    coverBlobUrl = URL.createObjectURL(file);
    useCoverPreview(coverBlobUrl);
    setCoverStatus("A imagem enviada será usada como capa ao salvar.", "ok");
  });

  /* ----------------------------------------------------------------------
     Voltar
     ---------------------------------------------------------------------- */
  $$("[data-go-back]").forEach((button) => {
    button.addEventListener("click", () => {
      if (window.history.length > 1) window.history.back();
      else window.location.assign("/");
    });
  });

  /* ----------------------------------------------------------------------
     Compartilhar citação como imagem
     ---------------------------------------------------------------------- */
  function readToken(name, fallback) {
    const value = getComputedStyle(root).getPropertyValue(name).trim();
    return value || fallback;
  }

  function wrapCanvasText(ctx, text, maxWidth) {
    const words = String(text || "").split(/\s+/).filter(Boolean);
    const lines = [];
    let current = "";
    words.forEach((word) => {
      const candidate = current ? `${current} ${word}` : word;
      if (ctx.measureText(candidate).width <= maxWidth) {
        current = candidate;
      } else {
        if (current) lines.push(current);
        current = word;
      }
    });
    if (current) lines.push(current);
    return lines;
  }

  async function buildQuoteCanvas(quote, source, tags, typeLabel) {
    if (document.fonts && document.fonts.ready) {
      try {
        await document.fonts.ready;
      } catch (error) {
        /* segue com as fontes disponíveis */
      }
    }

    const width = 1080;
    const height = 1350;
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");

    const paper = readToken("--lb-paper", "#f2ebdc");
    const ink = readToken("--lb-ink", "#201c16");
    const forest = readToken("--lb-forest", "#1e4a3c");
    const gold = readToken("--lb-gold", "#d6a24a");
    const muted = readToken("--lb-ink-3", "#6b6152");

    ctx.fillStyle = paper;
    ctx.fillRect(0, 0, width, height);

    // textura discreta
    ctx.globalAlpha = 0.05;
    ctx.fillStyle = ink;
    for (let index = 0; index < 900; index += 1) {
      const x = (index * 149) % width;
      const y = (index * 283) % height;
      ctx.fillRect(x, y, 1.4, 1.4);
    }
    ctx.globalAlpha = 1;

    // faixa editorial
    ctx.fillStyle = forest;
    ctx.fillRect(60, 0, 18, height);
    ctx.fillStyle = gold;
    ctx.fillRect(60, 0, 6, height);

    // cabeçalho
    ctx.fillStyle = muted;
    ctx.font = "600 22px Inter, sans-serif";
    ctx.letterSpacing = "6px";
    ctx.fillText("LEOBOOKS · CADERNO DE LEITURA", 130, 108);
    ctx.letterSpacing = "0px";
    ctx.strokeStyle = "rgba(32,28,22,0.18)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(130, 142);
    ctx.lineTo(width - 100, 142);
    ctx.stroke();

    // aspas
    ctx.fillStyle = gold;
    ctx.font = "italic 220px Fraunces, Georgia, serif";
    ctx.globalAlpha = 0.9;
    ctx.fillText("“", 112, 380);
    ctx.globalAlpha = 1;

    // tipo
    ctx.fillStyle = muted;
    ctx.font = "600 20px Inter, sans-serif";
    ctx.letterSpacing = "4px";
    ctx.fillText((typeLabel || "CITAÇÃO").toUpperCase(), 132, 430);
    ctx.letterSpacing = "0px";

    // texto
    const quoteText = String(quote || "").trim();
    let fontSize = quoteText.length > 520 ? 40 : quoteText.length > 320 ? 46 : quoteText.length > 180 ? 52 : 58;
    ctx.font = `italic ${fontSize}px Newsreader, Georgia, serif`;
    let lines = wrapCanvasText(ctx, quoteText, width - 290);
    while (lines.length > 12 && fontSize > 30) {
      fontSize -= 3;
      ctx.font = `italic ${fontSize}px Newsreader, Georgia, serif`;
      lines = wrapCanvasText(ctx, quoteText, width - 290);
    }

    ctx.fillStyle = ink;
    const lineHeight = Math.round(fontSize * 1.42);
    let y = 520;
    lines.slice(0, 14).forEach((line) => {
      ctx.fillText(line, 132, y);
      y += lineHeight;
    });
    if (lines.length > 14) {
      ctx.fillText("…", 132, y);
      y += lineHeight;
    }

    // fonte
    const sourceText = String(source || "").trim();
    ctx.fillStyle = muted;
    ctx.font = "500 25px Inter, sans-serif";
    const sourceLines = wrapCanvasText(ctx, sourceText, width - 290);
    if (sourceLines.length) {
      y += 46;
      const barY = y - 20;
      ctx.fillStyle = gold;
      ctx.fillRect(132, barY, 46, 3);
      ctx.fillStyle = ink;
      ctx.font = "italic 30px Fraunces, Georgia, serif";
      sourceLines.slice(0, 2).forEach((line, index) => {
        ctx.fillText(line, 132, y + 26 + index * 38);
      });
      y += 26 + Math.min(sourceLines.length, 2) * 38;
    }

    // tags
    const tagList = String(tags || "")
      .split("·")
      .map((tag) => tag.trim())
      .filter(Boolean)
      .slice(0, 4);
    if (tagList.length) {
      y += 26;
      ctx.font = "500 22px Inter, sans-serif";
      let x = 132;
      tagList.forEach((tag) => {
        const label = `#${tag.replace(/\s+/g, "")}`;
        const textWidth = ctx.measureText(label).width;
        ctx.strokeStyle = "rgba(32,28,22,0.28)";
        ctx.lineWidth = 1;
        ctx.strokeRect(x, y - 22, textWidth + 26, 38);
        ctx.fillStyle = muted;
        ctx.fillText(label, x + 13, y + 3);
        x += textWidth + 38;
      });
    }

    // rodapé
    ctx.strokeStyle = "rgba(32,28,22,0.16)";
    ctx.beginPath();
    ctx.moveTo(132, height - 132);
    ctx.lineTo(width - 100, height - 132);
    ctx.stroke();
    ctx.fillStyle = muted;
    ctx.font = "500 20px Inter, sans-serif";
    ctx.fillText("caderno de leitura", 132, height - 88);
    ctx.textAlign = "right";
    ctx.fillText("leobooks.local", width - 100, height - 88);
    ctx.textAlign = "left";

    // marca d'água discreta
    ctx.save();
    ctx.translate(width - 190, height - 250);
    ctx.rotate(-Math.PI / 2);
    ctx.fillStyle = muted;
    ctx.globalAlpha = 0.25;
    ctx.font = "500 18px Inter, sans-serif";
    ctx.fillText("LIDO E ANOTADO", 0, 0);
    ctx.restore();

    return canvas;
  }

  function shareFilename(button) {
    const clean = (value, max = 72) => String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, max);

    const book = clean(button.dataset.shareBook || "");
    const chapter = clean(button.dataset.shareChapter || "").replace(/^capitulo-/, "");
    const page = clean(button.dataset.sharePage || "");
    const parts = [];
    if (book) parts.push(book);
    if (chapter) parts.push(`capitulo-${chapter}`);
    if (page) parts.push(`pagina-${page}`);
    if (!parts.length) parts.push("citacao");
    parts.push("leobooks");
    return `${parts.join("-")}.png`;
  }

  async function shareQuote(button) {
    const quote = button.dataset.shareQuote || "";
    if (!quote) return;
    button.disabled = true;
    try {
      const canvas = await buildQuoteCanvas(
        quote,
        button.dataset.shareSource || "",
        button.dataset.shareTags || "",
        button.dataset.shareType || "Citação"
      );
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
      if (!blob) throw new Error("canvas");
      const filename = shareFilename(button);
      const file = new File([blob], filename, { type: "image/png" });
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        try {
          await navigator.share({ files: [file], title: "LeoBooks — citação" });
          notify("Citação compartilhada.", "success");
          return;
        } catch (shareError) {
          if (shareError && shareError.name === "AbortError") return;
        }
      }
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 2000);
      notify("Imagem da citação baixada.", "success");
    } catch (error) {
      notify("Não foi possível gerar a imagem agora.", "danger");
    } finally {
      button.disabled = false;
    }
  }

  $$("[data-share-quote]").forEach((button) => {
    button.addEventListener("click", () => shareQuote(button));
  });

  $$("[data-copy-quote]").forEach((button) => {
    button.addEventListener("click", async () => {
      const text = button.dataset.copyQuote || "";
      try {
        await navigator.clipboard.writeText(text);
        notify("Markdown copiado.", "success");
      } catch (error) {
        notify("Seu navegador bloqueou a cópia. Selecione o texto manualmente.", "warning");
      }
    });
  });

  /* ----------------------------------------------------------------------
     Tutorial de primeiro acesso
     ---------------------------------------------------------------------- */
  const onboardingModalEl = $("#onboardingModal");
  if (onboardingModalEl && window.bootstrap) {
    const steps = $$("[data-onboarding-step]", onboardingModalEl);
    const dots = $$("[data-onboarding-dot]", onboardingModalEl);
    const count = $("[data-onboarding-count]", onboardingModalEl);
    const prev = $("[data-onboarding-prev]", onboardingModalEl);
    const next = $("[data-onboarding-next]", onboardingModalEl);
    const finish = $("[data-onboarding-finish]", onboardingModalEl);
    let currentStep = 0;

    const renderOnboarding = () => {
      steps.forEach((step, index) => {
        step.hidden = index !== currentStep;
      });
      dots.forEach((dot, index) => {
        dot.classList.toggle("is-active", index === currentStep);
      });
      if (count) count.textContent = `${currentStep + 1} de ${steps.length}`;
      if (prev) prev.disabled = currentStep === 0;
      if (next) next.hidden = currentStep === steps.length - 1;
      if (finish) finish.hidden = currentStep !== steps.length - 1;
    };

    prev?.addEventListener("click", () => {
      currentStep = Math.max(0, currentStep - 1);
      renderOnboarding();
    });
    next?.addEventListener("click", () => {
      currentStep = Math.min(steps.length - 1, currentStep + 1);
      renderOnboarding();
    });

    renderOnboarding();
    const onboardingModal = bootstrap.Modal.getOrCreateInstance(onboardingModalEl, {
      backdrop: "static",
      keyboard: false,
    });
    window.setTimeout(() => onboardingModal.show(), 550);
  }

  /* ----------------------------------------------------------------------
     Pequenos ajustes de acessibilidade
     ---------------------------------------------------------------------- */
  $$(".modal").forEach((element) => {
    element.addEventListener("shown.bs.modal", () => {
      const focusable = element.querySelector("textarea, input:not([type=hidden]), button");
      if (focusable && !focusable.dataset.noFocus) {
        // deixa o Bootstrap cuidar do foco; apenas garantimos foco visível
      }
    });
  });

  if (reduceMotion) {
    document.documentElement.style.scrollBehavior = "auto";
  }
})();
