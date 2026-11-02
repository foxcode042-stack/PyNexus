(() => {
    const sidebar = document.getElementById("dashboard-sidebar");
    const menuToggle = document.getElementById("dashboard-menu-toggle");
    const scrim = document.getElementById("dashboard-scrim");

    const setMenuOpen = (isOpen) => {
        if (!sidebar || !menuToggle || !scrim) return;
        sidebar.classList.toggle("is-open", isOpen);
        menuToggle.setAttribute("aria-expanded", String(isOpen));
        menuToggle.setAttribute(
            "aria-label",
            isOpen ? "Close dashboard navigation" : "Open dashboard navigation",
        );
        scrim.hidden = !isOpen;
        document.body.classList.toggle("dashboard-menu-open", isOpen);
    };

    menuToggle?.addEventListener("click", () => {
        setMenuOpen(menuToggle.getAttribute("aria-expanded") !== "true");
    });
    scrim?.addEventListener("click", () => setMenuOpen(false));
    sidebar?.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", () => setMenuOpen(false));
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") setMenuOpen(false);
    });
    window.matchMedia("(min-width: 861px)").addEventListener("change", (event) => {
        if (event.matches) setMenuOpen(false);
    });

    const searchInput = document.getElementById("dashboard-search-input");
    const searchableItems = Array.from(
        document.querySelectorAll("[data-dashboard-searchable]"),
    );
    const emptyState = document.getElementById("dashboard-search-empty");
    searchInput?.addEventListener("input", () => {
        const query = searchInput.value.trim().toLocaleLowerCase();
        let visibleCount = 0;
        searchableItems.forEach((item) => {
            const matches = item.textContent?.toLocaleLowerCase().includes(query) ?? false;
            item.hidden = !matches;
            if (matches) visibleCount += 1;
        });
        if (emptyState) {
            emptyState.hidden = !query || visibleCount > 0;
        }
    });

    document.addEventListener("keydown", (event) => {
        if (
            event.key === "/" &&
            !(event.target instanceof HTMLInputElement) &&
            !(event.target instanceof HTMLTextAreaElement)
        ) {
            event.preventDefault();
            searchInput?.focus();
        }
    });
})();
