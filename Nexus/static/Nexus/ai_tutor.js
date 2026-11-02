(() => {
  const widget = document.querySelector("[data-ai-chat-widget]");
  if (!widget) return;

  const launcher = widget.querySelector("[data-widget-toggle]");
  const panel = widget.querySelector("[data-widget-panel]");
  const backdrop = widget.querySelector("[data-widget-backdrop]");
  const messagesElement = widget.querySelector("[data-widget-messages]");
  const feedback = widget.querySelector("[data-widget-feedback]");
  const form = widget.querySelector("[data-widget-form]");
  const input = widget.querySelector("[data-widget-input]");
  const sendButton = widget.querySelector("[data-widget-send]");
  const fileInput = widget.querySelector("[data-widget-file]");
  const attachmentElement = widget.querySelector("[data-widget-attachment]");
  const attachmentName = widget.querySelector("[data-attachment-name]");
  const historyElement = widget.querySelector("[data-chat-history]");
  const learningLevel = widget.querySelector("[data-learning-level]");
  const voiceInputButton = widget.querySelector("[data-voice-input]");
  const voiceRepliesButton = widget.querySelector("[data-voice-replies]");
  const fileLimit = 100_000;
  const allowedExtensions = new Set([
    ".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".csv",
  ]);
  const welcomeMessage = {
    role: "assistant",
    content: "Hi! I’m Nexus, your programming tutor. What would you like to learn? Ask me to explain a concept, debug code, plan a project, or create a practice exercise.",
  };
  let conversations = [{ id: Date.now(), title: "Welcome to Nexus AI", messages: [welcomeMessage] }];
  let activeConversationId = conversations[0].id;
  let attachment = null;
  let pending = false;
  let listening = false;
  let voiceReplies = false;
  let recognition = null;
  let dragged = false;
  let suppressLauncherClick = false;
  let dragState = null;
  let launcherPosition = null;
  let launcherAnchor = null;
  const launcherPositionKey = "nexus-ai-launcher-position";

  const activeConversation = () =>
    conversations.find((conversation) => conversation.id === activeConversationId) || conversations[0];

  const showFeedback = (message) => {
    feedback.hidden = !message;
    feedback.textContent = message;
  };

  const clampLauncherPosition = (left, top) => ({
    left: Math.max(0, Math.min(left, window.innerWidth - launcher.offsetWidth)),
    top: Math.max(0, Math.min(top, window.innerHeight - launcher.offsetHeight)),
  });

  const applyLauncherPosition = (left, top, save = false) => {
    launcherPosition = clampLauncherPosition(left, top);
    launcher.style.left = `${launcherPosition.left}px`;
    launcher.style.top = `${launcherPosition.top}px`;
    launcher.style.right = "auto";
    launcher.style.bottom = "auto";
    if (save) {
      try {
        localStorage.setItem(launcherPositionKey, JSON.stringify(launcherPosition));
      } catch {
        showFeedback("Your chat button moved, but this browser could not save its position.");
      }
    }
    positionPanelNearLauncher();
  };

  const loadLauncherPosition = () => {
    try {
      const saved = JSON.parse(localStorage.getItem(launcherPositionKey) || "null");
      if (saved && Number.isFinite(saved.left) && Number.isFinite(saved.top)) {
        applyLauncherPosition(saved.left, saved.top);
      }
    } catch {
      showFeedback("The saved chat button position could not be read; the default position is in use.");
    }
  };

  const positionPanelNearLauncher = (anchor = launcherAnchor) => {
    if (panel.hidden || window.matchMedia("(max-width: 680px)").matches) return;
    const launcherRect = anchor || launcher.getBoundingClientRect();
    const panelWidth = panel.offsetWidth;
    const panelHeight = panel.offsetHeight;
    const left = Math.max(8, Math.min(
      launcherRect.right - panelWidth,
      window.innerWidth - panelWidth - 8,
    ));
    const above = launcherRect.top - panelHeight - 12;
    const below = launcherRect.bottom + 12;
    const top = above >= 8
      ? above
      : below + panelHeight <= window.innerHeight - 8
        ? below
        : Math.max(8, Math.min(above, window.innerHeight - panelHeight - 8));
    panel.style.left = `${left}px`;
    panel.style.top = `${top}px`;
    panel.style.right = "auto";
    panel.style.bottom = "auto";
  };

  const getCookie = (name) => {
    const cookie = document.cookie.split("; ").find((item) => item.startsWith(`${name}=`));
    return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : "";
  };

  const getCsrfToken = async () => {
    let token = getCookie("csrftoken");
    if (token) return token;
    const response = await fetch(widget.dataset.csrfUrl, { credentials: "include" });
    if (!response.ok) throw new Error("Unable to start a secure request.");
    token = getCookie("csrftoken");
    if (!token) throw new Error("A security token could not be created. Reload the page and try again.");
    return token;
  };

  const appendInlineMarkdown = (parent, text) => {
    const pattern = /(\*\*[^*]+\*\*|`[^`]+`)/g;
    let cursor = 0;
    for (const match of text.matchAll(pattern)) {
      const start = match.index ?? 0;
      parent.append(document.createTextNode(text.slice(cursor, start)));
      const token = match[0];
      const element = token.startsWith("**") ? document.createElement("strong") : document.createElement("code");
      element.textContent = token.startsWith("**") ? token.slice(2, -2) : token.slice(1, -1);
      parent.append(element);
      cursor = start + token.length;
    }
    parent.append(document.createTextNode(text.slice(cursor)));
  };

  const appendTextBlock = (parent, block) => {
    const lines = block.split("\n");
    if (lines.every((line) => /^[-*]\s+/.test(line))) {
      const list = document.createElement("ul");
      lines.forEach((line) => {
        const item = document.createElement("li");
        appendInlineMarkdown(item, line.replace(/^[-*]\s+/, ""));
        list.append(item);
      });
      parent.append(list);
      return;
    }
    if (lines.every((line) => /^\d+[.)]\s+/.test(line))) {
      const list = document.createElement("ol");
      lines.forEach((line) => {
        const item = document.createElement("li");
        appendInlineMarkdown(item, line.replace(/^\d+[.)]\s+/, ""));
        list.append(item);
      });
      parent.append(list);
      return;
    }
    const paragraph = document.createElement("p");
    lines.forEach((line, index) => {
      if (index) paragraph.append(document.createElement("br"));
      appendInlineMarkdown(paragraph, line);
    });
    parent.append(paragraph);
  };

  const renderAssistantText = (container, text) => {
    const parts = text.split(/```([^\n`]*)\n([\s\S]*?)```/g);
    for (let index = 0; index < parts.length; index += 1) {
      if (index % 3 === 0) {
        parts[index].split(/\n{2,}/).filter(Boolean).forEach((block) => appendTextBlock(container, block));
      } else if (index % 3 === 1) {
        const code = document.createElement("div");
        code.className = "nexus-ai-code";
        const language = document.createElement("small");
        language.className = "nexus-ai-code-label";
        language.textContent = parts[index] || "code";
        const pre = document.createElement("pre");
        pre.textContent = parts[index + 1];
        code.append(language, pre);
        container.append(code);
        index += 1;
      }
    }
  };

  const renderMessage = (message) => {
    const row = document.createElement("article");
    row.className = `nexus-ai-message nexus-ai-message--${message.role}`;
    if (message.role === "assistant") {
      const avatar = document.createElement("span");
      avatar.className = "nexus-ai-avatar";
      avatar.setAttribute("aria-hidden", "true");
      const image = document.createElement("img");
      image.src = widget.querySelector(".nexus-ai-mark img").src;
      image.alt = "";
      avatar.append(image);
      row.append(avatar);
    }
    const bubble = document.createElement("div");
    bubble.className = "nexus-ai-bubble";
    if (message.role === "assistant") {
      renderAssistantText(bubble, message.content);
    } else {
      const paragraph = document.createElement("p");
      paragraph.textContent = message.content;
      bubble.append(paragraph);
      if (message.attachmentName) {
        const fileLabel = document.createElement("p");
        fileLabel.textContent = `Attached: ${message.attachmentName}`;
        bubble.append(fileLabel);
      }
    }
    row.append(bubble);
    messagesElement.append(row);
  };

  const renderHistory = () => {
    historyElement.replaceChildren();
    if (!conversations.length) {
      const empty = document.createElement("p");
      empty.className = "nexus-ai-history-empty";
      empty.textContent = "Your conversations will appear here.";
      historyElement.append(empty);
      return;
    }
    conversations.forEach((conversation) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "nexus-ai-history-item";
      button.dataset.conversationId = String(conversation.id);
      if (conversation.id === activeConversationId) button.setAttribute("aria-current", "true");
      button.textContent = conversation.title;
      historyElement.append(button);
    });
  };

  const renderSuggestions = () => {
    const suggestions = document.createElement("div");
    suggestions.className = "nexus-ai-suggestions";
    ["Explain Python loops", "Help me debug an error", "Suggest a project idea"].forEach((text) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "nexus-ai-suggestion";
      button.dataset.suggestion = text;
      button.textContent = text;
      suggestions.append(button);
    });
    messagesElement.append(suggestions);
  };

  const renderConversation = () => {
    messagesElement.replaceChildren();
    activeConversation().messages.forEach(renderMessage);
    if (activeConversation().messages.length === 1) renderSuggestions();
    messagesElement.scrollTop = messagesElement.scrollHeight;
    renderHistory();
    updateSendButton();
  };

  const updateSendButton = () => {
    sendButton.disabled = pending || (!input.value.trim() && !attachment);
  };

  const setAttachment = (file, content) => {
    attachment = { name: file.name, type: file.type || "text/plain", content };
    attachmentName.textContent = file.name;
    attachmentElement.hidden = false;
    updateSendButton();
  };

  const clearAttachment = () => {
    attachment = null;
    fileInput.value = "";
    attachmentElement.hidden = true;
    attachmentName.textContent = "";
    updateSendButton();
  };

  const setListening = (value) => {
    listening = value;
    voiceInputButton.setAttribute("aria-pressed", String(value));
    voiceInputButton.setAttribute("aria-label", value ? "Stop listening" : "Speak your question");
    voiceInputButton.title = value ? "Stop listening" : "Speak your question";
  };

  const speak = (text) => {
    if (!voiceReplies || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const spokenText = text
      .replace(/```[\s\S]*?```/g, "Code example available on screen.")
      .replace(/[*`#]/g, "");
    const utterance = new SpeechSynthesisUtterance(spokenText);
    utterance.rate = 0.95;
    window.speechSynthesis.speak(utterance);
  };

  const openWidget = () => {
    launcherAnchor = launcher.getBoundingClientRect();
    panel.hidden = false;
    backdrop.hidden = false;
    launcher.hidden = true;
    launcher.setAttribute("aria-expanded", "true");
    positionPanelNearLauncher(launcherAnchor);
    input.focus();
  };

  const closeWidget = () => {
    panel.hidden = true;
    backdrop.hidden = true;
    panel.classList.remove("nexus-ai-history-open");
    launcher.hidden = false;
    launcher.setAttribute("aria-expanded", "false");
    if (launcherPosition) {
      applyLauncherPosition(launcherPosition.left, launcherPosition.top, true);
    }
    if (recognition && listening) recognition.stop();
    setListening(false);
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    launcher.focus();
  };

  const newConversation = () => {
    const conversation = {
      id: Date.now(),
      title: "New conversation",
      messages: [welcomeMessage],
    };
    conversations = [conversation, ...conversations];
    activeConversationId = conversation.id;
    clearAttachment();
    input.value = "";
    showFeedback("");
    panel.classList.remove("nexus-ai-history-open");
    renderConversation();
    input.focus();
  };

  const submit = async () => {
    const question = input.value.trim();
    if ((!question && !attachment) || pending) return;

    showFeedback("");
    const selectedAttachment = attachment;
    const userMessage = {
      role: "user",
      content: question || `Please review the attached file: ${selectedAttachment.name}`,
      ...(selectedAttachment ? { attachmentName: selectedAttachment.name } : {}),
    };
    const conversation = activeConversation();
    conversation.messages.push(userMessage);
    if (conversation.title === "New conversation") {
      conversation.title = (question || `Review ${selectedAttachment.name}`).slice(0, 34);
    }
    const requestMessages = conversation.messages
      .map(({ role, content }) => ({ role, content }))
      .slice(-20);
    input.value = "";
    clearAttachment();
    pending = true;
    updateSendButton();
    renderConversation();
    const typing = document.createElement("div");
    typing.className = "nexus-ai-typing";
    typing.setAttribute("role", "status");
    typing.setAttribute("aria-label", "Nexus AI is preparing a response");
    for (let index = 0; index < 3; index += 1) typing.append(document.createElement("i"));
    messagesElement.append(typing);
    messagesElement.scrollTop = messagesElement.scrollHeight;

    try {
      const csrfToken = await getCsrfToken();
      const response = await fetch(widget.dataset.chatUrl, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({
          messages: requestMessages,
          learning_level: learningLevel.value,
          attachment: selectedAttachment,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "The tutor could not answer right now.");
      if (typeof data.message !== "string" || !data.message) {
        throw new Error("The tutor returned an invalid response. Please try again.");
      }
      conversation.messages.push({ role: "assistant", content: data.message });
      speak(data.message);
    } catch (error) {
      showFeedback(error instanceof Error ? error.message : "The tutor could not answer right now.");
    } finally {
      pending = false;
      typing.remove();
      renderConversation();
      input.focus();
    }
  };

  const startListening = () => {
    if (listening) {
      recognition?.stop();
      return;
    }
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      showFeedback("Voice input is not supported by this browser. You can still type your question.");
      return;
    }
    recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.onresult = (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript;
      if (transcript) {
        input.value = `${input.value}${input.value ? " " : ""}${transcript}`;
        updateSendButton();
      }
    };
    recognition.onend = () => setListening(false);
    recognition.onerror = () => {
      setListening(false);
      showFeedback("I could not hear that. Check microphone permission and try again.");
    };
    const beginListening = () => {
      if (!listening) return;
      try {
        recognition.start();
      } catch {
        setListening(false);
        showFeedback("The microphone could not be started. Check browser permission and try again.");
      }
    };
    try {
      setListening(true);
      showFeedback("");
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
        const prompt = new SpeechSynthesisUtterance("What would you like to learn?");
        prompt.onend = beginListening;
        prompt.onerror = beginListening;
        window.speechSynthesis.speak(prompt);
      } else {
        beginListening();
      }
    } catch {
      setListening(false);
      showFeedback("The microphone could not be started. Check browser permission and try again.");
    }
  };

  launcher.addEventListener("click", openWidget);
  launcher.addEventListener("pointerdown", (event) => {
    if (event.button !== 0 || event.target.closest("a")) return;
    const rect = launcher.getBoundingClientRect();
    dragState = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      left: rect.left,
      top: rect.top,
      moved: false,
    };
    launcher.setPointerCapture(event.pointerId);
  });
  launcher.addEventListener("pointermove", (event) => {
    if (!dragState || dragState.pointerId !== event.pointerId) return;
    const deltaX = event.clientX - dragState.startX;
    const deltaY = event.clientY - dragState.startY;
    if (!dragState.moved && Math.hypot(deltaX, deltaY) < 6) return;
    dragState.moved = true;
    dragged = true;
    event.preventDefault();
    applyLauncherPosition(dragState.left + deltaX, dragState.top + deltaY);
  });
  const finishLauncherDrag = (event) => {
    if (!dragState || dragState.pointerId !== event.pointerId) return;
    if (dragState.moved && launcherPosition) {
      applyLauncherPosition(launcherPosition.left, launcherPosition.top, true);
      suppressLauncherClick = true;
      window.setTimeout(() => {
        suppressLauncherClick = false;
        dragged = false;
      }, 0);
    }
    dragState = null;
  };
  launcher.addEventListener("pointerup", finishLauncherDrag);
  launcher.addEventListener("pointercancel", finishLauncherDrag);
  launcher.addEventListener("click", (event) => {
    if (suppressLauncherClick || dragged) {
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  }, true);
  launcher.addEventListener("keydown", (event) => {
    const movements = {
      ArrowLeft: [-32, 0],
      ArrowRight: [32, 0],
      ArrowUp: [0, -32],
      ArrowDown: [0, 32],
    };
    const movement = movements[event.key];
    if (!movement) return;
    event.preventDefault();
    const rect = launcher.getBoundingClientRect();
    applyLauncherPosition(rect.left + movement[0], rect.top + movement[1], true);
  });
  window.addEventListener("resize", () => {
    if (launcherPosition && !launcher.hidden) {
      applyLauncherPosition(launcherPosition.left, launcherPosition.top, true);
    }
    if (!launcher.hidden) launcherAnchor = launcher.getBoundingClientRect();
    else if (launcherPosition && launcherAnchor) {
      const position = clampLauncherPosition(launcherPosition.left, launcherPosition.top);
      launcherAnchor = {
        ...launcherAnchor,
        left: position.left,
        right: position.left + launcherAnchor.width,
        top: position.top,
        bottom: position.top + launcherAnchor.height,
      };
    }
    positionPanelNearLauncher();
  });
  loadLauncherPosition();
  widget.querySelector("[data-close-widget]").addEventListener("click", closeWidget);
  widget.querySelector("[data-close-sidebar]").addEventListener("click", () =>
    panel.classList.remove("nexus-ai-history-open"));
  widget.querySelector("[data-show-history]").addEventListener("click", () =>
    panel.classList.add("nexus-ai-history-open"));
  widget.querySelector("[data-new-chat]").addEventListener("click", newConversation);
  widget.querySelector("[data-attach-file]").addEventListener("click", () => fileInput.click());
  widget.querySelector("[data-remove-attachment]").addEventListener("click", clearAttachment);
  voiceInputButton.addEventListener("click", startListening);
  voiceRepliesButton.addEventListener("click", () => {
    voiceReplies = !voiceReplies;
    voiceRepliesButton.setAttribute("aria-pressed", String(voiceReplies));
    voiceRepliesButton.setAttribute(
      "aria-label",
      voiceReplies ? "Disable spoken replies" : "Enable spoken replies",
    );
    voiceRepliesButton.title = voiceReplies ? "Disable spoken replies" : "Enable spoken replies";
    if (!voiceReplies && "speechSynthesis" in window) window.speechSynthesis.cancel();
  });
  backdrop.addEventListener("click", closeWidget);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    void submit();
  });
  input.addEventListener("input", updateSendButton);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submit();
    }
  });
  fileInput.addEventListener("change", async () => {
    const file = fileInput.files?.[0];
    if (!file) return;
    const extension = file.name.includes(".") ? `.${file.name.split(".").pop().toLowerCase()}` : "";
    if (!allowedExtensions.has(extension)) {
      clearAttachment();
      showFeedback("Choose a supported text or code file.");
      return;
    }
    if (file.size > fileLimit) {
      clearAttachment();
      showFeedback("Choose a text or code file smaller than 100 KB.");
      return;
    }
    try {
      const content = await file.text();
      if (content.length > fileLimit) {
        clearAttachment();
        showFeedback("Choose a text or code file smaller than 100 KB.");
        return;
      }
      setAttachment(file, content);
      showFeedback("");
    } catch {
      clearAttachment();
      showFeedback("This file could not be read as text.");
    }
  });
  historyElement.addEventListener("click", (event) => {
    const button = event.target.closest("[data-conversation-id]");
    if (!button) return;
    activeConversationId = Number(button.dataset.conversationId);
    panel.classList.remove("nexus-ai-history-open");
    showFeedback("");
    renderConversation();
  });
  messagesElement.addEventListener("click", (event) => {
    const button = event.target.closest("[data-suggestion]");
    if (!button) return;
    input.value = button.dataset.suggestion;
    updateSendButton();
    input.focus();
  });
  document.querySelectorAll("[data-open-ai-tutor]").forEach((button) => {
    button.addEventListener("click", openWidget);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) closeWidget();
  });
  window.addEventListener("open-ai-tutor", openWidget);
  window.addEventListener("pagehide", () => {
    if (recognition && listening) recognition.stop();
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  });

  renderConversation();
})();
