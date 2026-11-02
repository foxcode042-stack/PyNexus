(() => {
    const dialog = document.getElementById("welcome-dialog");
    const cookieBanner = document.getElementById("cookie-banner");
    const homeStorageKey = "technonexus-welcome-dismissed";
    const cookieStorageKey = "technonexus-cookie-consent";

    const rememberDismissal = () => {
        try {
            window.localStorage.setItem(homeStorageKey, "true");
        } catch (error) {
            console.error("Could not save the welcome guide preference.", error);
        }
    };

    const setCookieConsent = (value) => {
        try {
            window.localStorage.setItem(cookieStorageKey, value);
        } catch (error) {
            console.error("Could not save the cookie consent preference.", error);
        }
    };

    const hideCookieBanner = () => {
        if (cookieBanner) {
            cookieBanner.classList.remove("visible");
        }
    };

    if (cookieBanner) {
        try {
            if (window.localStorage.getItem(cookieStorageKey) === "accepted") {
                hideCookieBanner();
            } else {
                cookieBanner.classList.add("visible");
            }
        } catch (error) {
            console.error("Could not read the cookie consent preference.", error);
            cookieBanner.classList.add("visible");
        }

        document.querySelectorAll("[data-cookie-accept]").forEach((button) => {
            button.addEventListener("click", () => {
                setCookieConsent("accepted");
                hideCookieBanner();
            });
        });

        document.querySelectorAll("[data-cookie-dismiss]").forEach((button) => {
            button.addEventListener("click", () => {
                setCookieConsent("dismissed");
                hideCookieBanner();
            });
        });
    }

    if (!(dialog instanceof HTMLDialogElement)) {
        return;
    }

    try {
        if (window.localStorage.getItem(homeStorageKey) !== "true") {
            dialog.showModal();
        }
    } catch (error) {
        console.error("Could not read the welcome guide preference.", error);
        dialog.showModal();
    }

    dialog.querySelectorAll("[data-welcome-close]").forEach((button) => {
        button.addEventListener("click", () => dialog.close());
    });

    dialog.addEventListener("close", rememberDismissal);
    dialog.addEventListener("click", (event) => {
        if (event.target === dialog) {
            dialog.close();
        }
    });
    dialog.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", rememberDismissal);
    });

    const menu = document.getElementById("nav-menu");
    const menuToggle = document.getElementById("hamburger");
    const closeMenu = () => {
        if (menu && menuToggle) {
            menu.classList.remove("active");
            menuToggle.setAttribute("aria-expanded", "false");
            menuToggle.setAttribute("aria-label", "Open navigation menu");
        }
    };

    if (menu && menuToggle) {
        menuToggle.addEventListener("click", () => {
            const isOpen = menu.classList.toggle("active");
            menuToggle.setAttribute("aria-expanded", String(isOpen));
            menuToggle.setAttribute("aria-label", isOpen ? "Close navigation menu" : "Open navigation menu");
        });
        menu.querySelectorAll("a").forEach((link) => link.addEventListener("click", closeMenu));
        document.addEventListener("click", (event) => {
            if (!menu.contains(event.target) && !menuToggle.contains(event.target)) {
                closeMenu();
            }
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                closeMenu();
                closeDropdown();
            }
        });
    }

    const dropdownToggle = document.querySelector(".dropdown-toggle");
    const dropdownMenu = document.querySelector(".dropdown-menu");
    const closeDropdown = () => {
        if (dropdownToggle && dropdownMenu) {
            dropdownToggle.setAttribute("aria-expanded", "false");
            dropdownMenu.classList.remove("show");
        }
    };
    if (dropdownToggle && dropdownMenu) {
        dropdownToggle.addEventListener("click", (event) => {
            event.preventDefault();
            const isOpen = dropdownToggle.getAttribute("aria-expanded") !== "true";
            dropdownToggle.setAttribute("aria-expanded", String(isOpen));
            dropdownMenu.classList.toggle("show", isOpen);
        });
        document.addEventListener("click", (event) => {
            if (!dropdownToggle.contains(event.target) && !dropdownMenu.contains(event.target)) {
                closeDropdown();
            }
        });
    }

    const themeToggle = document.getElementById("theme-toggle");
    if (themeToggle) {
        const themeIcon = themeToggle.querySelector("i");
        const setTheme = (theme) => {
            document.body.dataset.theme = theme;
            const isDark = theme === "dark";
            themeToggle.setAttribute("aria-label", `Switch to ${isDark ? "light" : "dark"} theme`);
            themeToggle.title = `Switch to ${isDark ? "light" : "dark"} theme`;
            if (themeIcon) {
                themeIcon.className = `fas fa-${isDark ? "sun" : "moon"}`;
            }
        };
        try {
            setTheme(window.localStorage.getItem("technonexus-theme") === "dark" ? "dark" : "light");
        } catch (error) {
            console.error("Could not read the theme preference.", error);
            setTheme("light");
        }
        themeToggle.addEventListener("click", () => {
            const nextTheme = document.body.dataset.theme === "dark" ? "light" : "dark";
            setTheme(nextTheme);
            try {
                window.localStorage.setItem("technonexus-theme", nextTheme);
            } catch (error) {
                console.error("Could not save the theme preference.", error);
            }
        });
    }

    const courseTabs = document.querySelectorAll(".course-tab");
    const courseCards = document.querySelectorAll(".course-card[data-category]");
    courseTabs.forEach((tab) => {
        tab.setAttribute("aria-pressed", String(tab.classList.contains("active")));
        tab.addEventListener("click", () => {
            const category = tab.dataset.category;
            courseTabs.forEach((item) => {
                const isActive = item === tab;
                item.classList.toggle("active", isActive);
                item.setAttribute("aria-pressed", String(isActive));
            });
            courseCards.forEach((card) => {
                const isVisible = category === "all" || card.dataset.category === category;
                card.hidden = !isVisible;
                if (isVisible) {
                    card.classList.remove("filter-in");
                    window.requestAnimationFrame(() => card.classList.add("filter-in"));
                }
            });
        });
    });

    const carousel = document.getElementById("project-carousel");
    const slides = carousel ? Array.from(carousel.querySelectorAll(".project-slide")) : [];
    const carouselDots = Array.from(document.querySelectorAll("[data-carousel-slide]"));
    if (carousel && slides.length) {
        let activeSlide = Math.max(0, slides.findIndex((slide) => slide.classList.contains("is-active")));
        const showSlide = (index) => {
            activeSlide = (index + slides.length) % slides.length;
            slides.forEach((slide, slideIndex) => {
                const isActive = slideIndex === activeSlide;
                slide.classList.toggle("is-active", isActive);
                slide.setAttribute("aria-hidden", String(!isActive));
            });
            carouselDots.forEach((dot, dotIndex) => {
                const isActive = dotIndex === activeSlide;
                dot.classList.toggle("is-active", isActive);
                if (isActive) {
                    dot.setAttribute("aria-current", "true");
                } else {
                    dot.removeAttribute("aria-current");
                }
            });
        };
        document.querySelector("[data-carousel-prev]")?.addEventListener("click", () => showSlide(activeSlide - 1));
        document.querySelector("[data-carousel-next]")?.addEventListener("click", () => showSlide(activeSlide + 1));
        carouselDots.forEach((dot) => {
            dot.addEventListener("click", () => showSlide(Number(dot.dataset.carouselSlide)));
        });
        carousel.addEventListener("keydown", (event) => {
            if (event.key === "ArrowLeft") showSlide(activeSlide - 1);
            if (event.key === "ArrowRight") showSlide(activeSlide + 1);
        });
        showSlide(activeSlide);
    }

    const contactForm = document.getElementById("contact-form");
    if (contactForm instanceof HTMLFormElement) {
        contactForm.addEventListener("submit", (event) => {
            event.preventDefault();
            if (!contactForm.reportValidity()) return;
            const formData = new FormData(contactForm);
            const recipient = contactForm.dataset.contactEmail;
            if (!recipient) {
                console.error("Contact form recipient is not configured.");
                return;
            }
            const subject = String(formData.get("subject") || "Website enquiry");
            const body = [
                `Name: ${formData.get("name")}`,
                `Email: ${formData.get("email")}`,
                "",
                String(formData.get("message") || ""),
            ].join("\n");
            window.location.href = `mailto:${recipient}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
        });
    }

    const revealElements = document.querySelectorAll(
        ".reveal, .feature-item, .course-card, .mv-card, .learning-image-card"
    );
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        revealElements.forEach((element) => element.classList.add("visible"));
    } else if ("IntersectionObserver" in window) {
        const revealObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add("visible");
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12 });
        revealElements.forEach((element) => revealObserver.observe(element));
    } else {
        revealElements.forEach((element) => element.classList.add("visible"));
    }

    const navbar = document.getElementById("navbar");
    const backToTop = document.getElementById("back-to-top");
    const updateScrollState = () => {
        const isScrolled = window.scrollY > 24;
        if (navbar) navbar.classList.toggle("scrolled", isScrolled);
        if (backToTop) backToTop.classList.toggle("visible", window.scrollY > 400);
    };
    window.addEventListener("scroll", updateScrollState, { passive: true });
    updateScrollState();

    const typewriter = document.getElementById("typewriter");
    const phrases = ["web development", "Python & Django", "software projects", "creative technology"];
    if (typewriter && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        let phraseIndex = 0;
        window.setInterval(() => {
            phraseIndex = (phraseIndex + 1) % phrases.length;
            typewriter.classList.add("typewriter-changing");
            window.setTimeout(() => {
                typewriter.textContent = phrases[phraseIndex];
                typewriter.classList.remove("typewriter-changing");
            }, 180);
        }, 2800);
    }
})();