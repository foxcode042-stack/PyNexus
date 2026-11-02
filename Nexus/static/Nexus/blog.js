(() => {
  const body = document.body;
  const apiBase = (body.dataset.apiBase || "/api").replace(/\/+$/, "");
  const csrfUrl = body.dataset.csrfUrl || `${apiBase}/csrf/`;
  const index = document.querySelector("[data-blog-index]");
  const reader = document.querySelector("[data-blog-reader]");
  const searchInput = document.querySelector("[data-blog-search]");
  const cards = [...document.querySelectorAll("[data-article-card]")];
  const categories = [...document.querySelectorAll(".blog-category[data-category]")];
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let selectedId = null;
  let selectedCard = null;
  let speaking = false;

  const storageRead = (key, fallback) => {
    try {
      const value = JSON.parse(window.localStorage.getItem(key) || "null");
      return value ?? fallback;
    } catch {
      return fallback;
    }
  };
  const storageWrite = (key, value) => {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
      return false;
    }
    return true;
  };
  const getCookie = (name) => {
    const cookie = document.cookie.split("; ").find((item) => item.startsWith(`${name}=`));
    return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : "";
  };
  const showNotice = (message) => {
    const notice = reader.querySelector("[data-article-feedback]");
    if (!notice) return;
    notice.hidden = false;
    notice.textContent = message;
  };

  const filterArticles = () => {
    const term = (searchInput?.value || "").trim().toLocaleLowerCase();
    const activeCategory = categories.find((button) => button.getAttribute("aria-pressed") === "true")
      ?.dataset.category || "All articles";
    let visible = 0;
    cards.forEach((card) => {
      const categoryMatch = activeCategory === "All articles" || card.dataset.category === activeCategory;
      const searchable = `${card.dataset.title} ${card.dataset.excerpt} ${card.dataset.category}`.toLocaleLowerCase();
      const searchMatch = !term || searchable.includes(term);
      card.hidden = !(categoryMatch && searchMatch);
      if (!card.hidden) visible += 1;
    });

    document.querySelector("[data-empty-state]").hidden = visible > 0;
    document.querySelector("[data-results-count]").textContent =
      `${visible} practical guide${visible === 1 ? "" : "s"} ready to explore`;
    document.querySelector("[data-results-heading]").textContent =
      term || activeCategory !== "All articles" ? "Search results" : "Latest articles";
    document.querySelector("[data-clear-filters]").hidden =
      !term && activeCategory === "All articles";
  };

  const createCommentCard = (text, timestamp) => {
    const article = document.createElement("article");
    article.className = "blog-comment";
    const avatar = document.createElement("span");
    avatar.className = "blog-comment-avatar";
    avatar.textContent = "YOU";
    const content = document.createElement("div");
    const heading = document.createElement("div");
    heading.className = "blog-comment-heading";
    const name = document.createElement("strong");
    name.textContent = "You";
    const time = document.createElement("time");
    time.textContent = timestamp;
    heading.append(name, time);
    const paragraph = document.createElement("p");
    paragraph.textContent = text;
    content.append(heading, paragraph);
    article.append(avatar, content);
    return article;
  };

  const renderComments = () => {
    const key = `tech-nexus-blog-comments-${selectedId}`;
    const commentsForArticle = storageRead(key, []);
    const list = reader.querySelector("[data-comment-list]");
    list.replaceChildren(...commentsForArticle.map((comment) =>
      createCommentCard(comment.text, comment.timestamp),
    ));
    reader.querySelector("[data-comment-count]").textContent =
      `(${commentsForArticle.length})`;
  };

  const updateFeedbackButtons = () => {
    const liked = storageRead("tech-nexus-blog-likes", []).includes(selectedId);
    const bookmarked = storageRead("tech-nexus-blog-bookmarks", []).includes(selectedId);
    reader.querySelectorAll("[data-like-article]").forEach((button) => {
      button.setAttribute("aria-pressed", String(liked));
      button.querySelector("span").textContent = liked ? "Liked" : "Like";
      button.firstChild.textContent = liked ? "♥ " : "♡ ";
    });
    reader.querySelectorAll("[data-bookmark-article]").forEach((button) => {
      button.setAttribute("aria-pressed", String(bookmarked));
      const label = button.querySelector("span");
      if (label) label.textContent = bookmarked ? "Saved to library" : "Save for later";
      else button.textContent = bookmarked ? "▣" : "♧";
    });
  };

  const setReaderProgress = () => {
    const bar = document.querySelector("[data-reading-progress]");
    if (!selectedId) {
      bar.hidden = true;
      return;
    }
    const scrollable = document.documentElement.scrollHeight - window.innerHeight;
    const progress = scrollable > 0 ? Math.min(100, Math.max(0, (window.scrollY / scrollable) * 100)) : 0;
    bar.style.width = `${progress}%`;
    bar.hidden = false;
  };

  const openArticle = (id, updateHistory = true) => {
    const card = cards.find((item) => item.dataset.articleId === String(id));
    if (!card) return;
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    speaking = false;
    selectedId = card.dataset.articleId;
    selectedCard = card;
    index.hidden = true;
    reader.hidden = false;
    reader.querySelector("[data-reader-category]").textContent = card.dataset.category;
    reader.querySelector("[data-reader-title]").textContent = card.dataset.title;
    reader.querySelector("[data-reader-excerpt]").textContent = card.dataset.excerpt;
    reader.querySelector("[data-reader-author]").textContent = card.dataset.author;
    reader.querySelector("[data-reader-role]").textContent = card.dataset.role;
    reader.querySelector("[data-reader-date]").textContent = card.dataset.date;
    reader.querySelector("[data-reader-time]").textContent = card.dataset.readTime;
    reader.querySelector("[data-author-initials]").textContent = card.dataset.author
      .split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
    const image = reader.querySelector("[data-reader-image]");
    image.src = card.dataset.image;
    image.alt = card.dataset.imageAlt;

    const contentTemplate = document.querySelector("[data-article-content]");
    const content = contentTemplate.content.cloneNode(true);
    content.querySelector("[data-article-lead]").textContent = card.dataset.excerpt;
    const sectionsTemplate = document.querySelector(
      `[data-article-sections-for="${CSS.escape(selectedId)}"]`,
    );
    if (sectionsTemplate) {
      content.querySelector("[data-article-sections]").append(
        sectionsTemplate.content.cloneNode(true),
      );
    }
    reader.querySelector("[data-reader-content]").replaceChildren(content);
    reader.querySelector("[data-article-feedback]").hidden = true;
    renderComments();
    updateFeedbackButtons();
    renderRelated();
    if (updateHistory) {
      const url = new URL(window.location.href);
      url.searchParams.set("article", card.dataset.slug);
      window.history.pushState({ article: card.dataset.slug }, "", url);
    }
    window.scrollTo({ top: 0, behavior: reducedMotion ? "instant" : "smooth" });
    setReaderProgress();
  };

  const closeArticle = (updateHistory = true) => {
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    speaking = false;
    selectedId = null;
    selectedCard = null;
    reader.hidden = true;
    index.hidden = false;
    if (updateHistory) {
      const url = new URL(window.location.href);
      url.searchParams.delete("article");
      window.history.replaceState({}, "", url);
    }
    window.scrollTo({ top: 0, behavior: reducedMotion ? "instant" : "smooth" });
    setReaderProgress();
  };

  const renderRelated = () => {
    const related = cards.filter((card) => card.dataset.articleId !== selectedId).slice(0, 3);
    const target = reader.querySelector("[data-related-grid]");
    target.replaceChildren(...related.map((card) => {
      const copy = card.cloneNode(true);
      copy.hidden = false;
      return copy;
    }));
  };

  categories.forEach((button) => {
    button.addEventListener("click", () => {
      categories.forEach((category) => {
        const active = category === button;
        category.classList.toggle("is-active", active);
        category.setAttribute("aria-pressed", String(active));
      });
      filterArticles();
    });
  });

  searchInput?.addEventListener("input", filterArticles);
  document.querySelector("[data-blog-search-form]")?.addEventListener("submit", (event) => {
    event.preventDefault();
    document.querySelector("#latest").scrollIntoView({
      behavior: reducedMotion ? "instant" : "smooth",
    });
  });
  document.querySelectorAll("[data-search-term]").forEach((button) => {
    button.addEventListener("click", () => {
      searchInput.value = button.dataset.searchTerm;
      categories[0].click();
      filterArticles();
      document.querySelector("#latest").scrollIntoView({
        behavior: reducedMotion ? "instant" : "smooth",
      });
    });
  });
  document.querySelectorAll("[data-search-category]").forEach((button) => {
    button.addEventListener("click", () => {
      const category = button.dataset.searchCategory;
      categories.find((item) => item.dataset.category === category)?.click();
      document.querySelector("#latest").scrollIntoView({
        behavior: reducedMotion ? "instant" : "smooth",
      });
    });
  });
  document.querySelector("[data-clear-filters]")?.addEventListener("click", () => {
    searchInput.value = "";
    categories[0].click();
  });

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-open-article]");
    if (button) openArticle(button.dataset.openArticle);
    if (event.target.closest("[data-back-to-blog]")) closeArticle();
  });

  const themeToggle = document.querySelector("[data-theme-toggle]");
  const applyTheme = (theme) => {
    body.dataset.theme = theme;
    themeToggle.setAttribute("aria-label", theme === "dark" ? "Use light mode" : "Use dark mode");
    themeToggle.innerHTML = theme === "dark"
      ? '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>'
      : '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.5 15.5A8.5 8.5 0 0 1 8.5 3.5a8.5 8.5 0 1 0 12 12Z"/></svg>';
    storageWrite("tech-nexus-blog-theme", theme);
  };
  applyTheme(storageRead("tech-nexus-blog-theme", "light") === "dark" ? "dark" : "light");
  themeToggle?.addEventListener("click", () => {
    applyTheme(body.dataset.theme === "dark" ? "light" : "dark");
  });

  reader.querySelectorAll("[data-like-article]").forEach((button) => {
    button.addEventListener("click", () => {
      const likes = storageRead("tech-nexus-blog-likes", []);
      const next = likes.includes(selectedId)
        ? likes.filter((id) => id !== selectedId)
        : [...likes, selectedId];
      storageWrite("tech-nexus-blog-likes", next);
      updateFeedbackButtons();
    });
  });

  reader.querySelectorAll("[data-bookmark-article]").forEach((button) => {
    button.addEventListener("click", () => {
      const bookmarks = storageRead("tech-nexus-blog-bookmarks", []);
      const next = bookmarks.includes(selectedId)
        ? bookmarks.filter((id) => id !== selectedId)
        : [...bookmarks, selectedId];
      storageWrite("tech-nexus-blog-bookmarks", next);
      updateFeedbackButtons();
    });
  });

  reader.querySelectorAll("[data-share-article]").forEach((button) => {
    button.addEventListener("click", async () => {
      const data = {
        title: selectedCard?.dataset.title || "Tech-Nexus Academy Blog",
        url: window.location.href,
      };
      try {
        if (navigator.share) await navigator.share(data);
        else if (navigator.clipboard) {
          await navigator.clipboard.writeText(data.url);
          showNotice("Article link copied.");
        } else {
          showNotice(`Copy this article link: ${data.url}`);
        }
      } catch (error) {
        if (error.name !== "AbortError") showNotice("Unable to share this article from this browser.");
      }
    });
  });

  reader.querySelector("[data-listen-article]")?.addEventListener("click", (event) => {
    const button = event.currentTarget;
    if (!("speechSynthesis" in window)) {
      showNotice("Read-aloud is not supported by this browser.");
      return;
    }
    if (speaking) {
      window.speechSynthesis.cancel();
      speaking = false;
      button.querySelector("span").textContent = "Listen to article";
      return;
    }
    const content = reader.querySelector("[data-reader-content]").innerText;
    const speech = new SpeechSynthesisUtterance(
      `${selectedCard.dataset.title}. ${content}`,
    );
    speech.onend = () => {
      speaking = false;
      button.querySelector("span").textContent = "Listen to article";
    };
    speech.onerror = () => {
      speaking = false;
      button.querySelector("span").textContent = "Listen to article";
      showNotice("Read-aloud stopped because of a browser speech error.");
    };
    window.speechSynthesis.speak(speech);
    speaking = true;
    button.querySelector("span").textContent = "Stop listening";
  });

  reader.querySelector("[data-comment-form]")?.addEventListener("submit", (event) => {
    event.preventDefault();
    const textarea = event.currentTarget.querySelector("textarea");
    const text = textarea.value.trim();
    if (!text) return;
    const commentsForArticle = storageRead(
      `tech-nexus-blog-comments-${selectedId}`,
      [],
    );
    commentsForArticle.unshift({
      text,
      timestamp: new Date().toLocaleString(),
    });
    if (!storageWrite(`tech-nexus-blog-comments-${selectedId}`, commentsForArticle)) {
      showNotice("Comments could not be saved in this browser.");
      return;
    }
    textarea.value = "";
    renderComments();
  });

  document.querySelector("[data-newsletter-form]")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const input = form.elements.email;
    const button = form.querySelector('button[type="submit"]');
    const feedback = document.querySelector("[data-newsletter-feedback]");
    button.disabled = true;
    try {
      let csrfToken = getCookie("csrftoken");
      if (!csrfToken) {
        const csrfResponse = await fetch(csrfUrl, { credentials: "include" });
        if (!csrfResponse.ok) throw new Error("Unable to start a secure request.");
        csrfToken = getCookie("csrftoken");
      }
      const response = await fetch(`${apiBase}/blog/newsletter/`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ email: input.value.trim() }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "Unable to subscribe right now.");
      feedback.hidden = false;
      feedback.textContent = data.detail;
      form.hidden = true;
    } catch (error) {
      feedback.hidden = false;
      feedback.textContent = error.message || "Unable to subscribe right now.";
      feedback.setAttribute("role", "alert");
    } finally {
      button.disabled = false;
    }
  });

  window.addEventListener("scroll", setReaderProgress, { passive: true });
  window.addEventListener("popstate", () => {
    const slug = new URL(window.location.href).searchParams.get("article");
    if (!slug) {
      if (selectedId) closeArticle(false);
      return;
    }
    const card = cards.find((item) => item.dataset.slug === slug);
    if (card) openArticle(card.dataset.articleId, false);
  });

  const initialSlug = new URL(window.location.href).searchParams.get("article");
  const initialCard = cards.find((item) => item.dataset.slug === initialSlug);
  if (initialCard) openArticle(initialCard.dataset.articleId, false);
})();
