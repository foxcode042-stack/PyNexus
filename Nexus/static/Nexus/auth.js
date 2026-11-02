(() => {
  const root = document.body;
  const apiBase = (root.dataset.apiBase || "/api").replace(/\/+$/, "");
  const csrfUrl = root.dataset.csrfUrl || `${apiBase}/csrf/`;

  const getCookie = (name) => {
    const cookie = document.cookie
      .split("; ")
      .find((item) => item.startsWith(`${name}=`));
    return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : "";
  };

  const request = async (path, body) => {
    let csrfToken = getCookie("csrftoken");
    if (!csrfToken) {
      const csrfResponse = await fetch(csrfUrl, { credentials: "include" });
      if (!csrfResponse.ok) {
        throw new Error("Unable to start a secure request. Refresh the page and try again.");
      }
      csrfToken = getCookie("csrftoken");
    }

    const response = await fetch(`${apiBase}/auth/${path}/`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || "Unable to complete this request.");
    }
    return data;
  };

  const authApi = {
    login: (identifier, password, remember, next = "") =>
      request("login", { identifier, password, remember, next }),
    register: (details) => request("register", details),
    verifyEmail: (email, code) => request("verify-email", { email, code }),
    resendCode: (email) => request("resend-code", { email }),
    forgotPassword: (email) => request("forgot-password", { email }),
    logoutOtherDevices: () => request("sessions/logout-others", {}),
    logout: () => request("logout", {}),
    googleUrl: `${apiBase}/auth/google/`,
    githubUrl: `${apiBase}/auth/github/`,
  };

  const showFeedback = (card, message, isError = false) => {
    const feedback = card?.querySelector("[data-auth-feedback]");
    if (!feedback) return;
    feedback.hidden = false;
    feedback.textContent = message;
    feedback.setAttribute("role", isError ? "alert" : "status");
  };

  const makeCodeForm = (card, email, nextForm) => {
    card.querySelector(".auth-code-form")?.remove();
    const form = document.createElement("form");
    form.className = "auth-form auth-code-form";
    form.innerHTML = `
      <div class="auth-field">
        <label for="email-verification-code">Email verification code</label>
        <input id="email-verification-code" name="code" inputmode="numeric"
          autocomplete="one-time-code" pattern="[0-9]{6}" maxlength="6" required>
      </div>
      <button class="auth-submit" type="submit"><span>Verify and continue</span><span aria-hidden="true">→</span></button>
      <button class="auth-inline-button auth-resend-code" type="button">Send a new code</button>
    `;
    nextForm.insertAdjacentElement("afterend", form);
    nextForm.hidden = true;

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const code = new FormData(form).get("code")?.toString().trim() || "";
      try {
        const result = await authApi.verifyEmail(email, code);
        window.location.assign(result.redirect_url || "/login/");
      } catch (error) {
        showFeedback(card, error.message, true);
      }
    });

    form.querySelector(".auth-resend-code").addEventListener("click", async () => {
      const button = form.querySelector(".auth-resend-code");
      button.disabled = true;
      try {
        const result = await authApi.resendCode(email);
        showFeedback(card, result.detail || "A new code has been sent.");
      } catch (error) {
        showFeedback(card, error.message, true);
      } finally {
        button.disabled = false;
      }
    });
    form.querySelector("input").focus();
  };

  const loginForm = document.querySelector("[data-auth-login]");
  const registerForm = document.querySelector("[data-auth-register]");
  const card = document.querySelector(".auth-panel");

  if (registerForm) {
    const locationButton = registerForm.querySelector("[data-capture-location]");
    const locationStatus = registerForm.querySelector("[data-location-status]");
    locationButton?.addEventListener("click", () => {
      if (!navigator.geolocation) {
        locationStatus.textContent = "Location sharing is not available in this browser.";
        return;
      }

      locationButton.disabled = true;
      locationStatus.textContent = "Waiting for your permission and location…";
      navigator.geolocation.getCurrentPosition(
        ({ coords }) => {
          registerForm.elements.latitude.value = String(coords.latitude);
          registerForm.elements.longitude.value = String(coords.longitude);
          registerForm.elements.location_accuracy.value = String(coords.accuracy);
          registerForm.elements.location_captured_at.value = new Date().toISOString();
          locationStatus.textContent = `Location captured (about ${Math.round(coords.accuracy)} m accuracy).`;
          locationButton.disabled = false;
        },
        (error) => {
          const message = error.code === error.PERMISSION_DENIED
            ? "Location permission was denied. You can continue without sharing it."
            : "Could not capture your location. You can continue without sharing it.";
          locationStatus.textContent = message;
          locationButton.disabled = false;
        },
        { enableHighAccuracy: true, maximumAge: 0, timeout: 12000 },
      );
    });

    registerForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (locationButton?.disabled) {
        showFeedback(card, "Please wait for location capture to finish, or cancel it before continuing.", true);
        return;
      }
      const formData = new FormData(registerForm);
      const value = (name) => (formData.get(name) || "").toString().trim();
      const day = value("dob_day").padStart(2, "0");
      const month = value("dob_month").padStart(2, "0");
      const year = value("dob_year");
      const numberOrNull = (name) => {
        const raw = value(name);
        return raw === "" ? null : Number(raw);
      };
      const payload = {
        username: value("username"),
        email: value("email"),
        first_name: value("first_name"),
        last_name: value("last_name"),
        phone_number: value("phone_number"),
        country: value("country"),
        zip_code: value("zip_code"),
        occupation: value("occupation"),
        state: value("state"),
        location: value("location"),
        latitude: numberOrNull("latitude"),
        longitude: numberOrNull("longitude"),
        location_accuracy: numberOrNull("location_accuracy"),
        location_captured_at: value("location_captured_at") || null,
        date_of_birth: `${year}-${month}-${day}`,
        nationality: value("nationality"),
        password: value("password1"),
        password_confirmation: value("password2"),
      };

      if (payload.password !== payload.password_confirmation) {
        showFeedback(card, "The passwords do not match.", true);
        registerForm.elements.password2.focus();
        return;
      }

      const button = registerForm.querySelector('button[type="submit"]');
      button.disabled = true;
      try {
        const result = await authApi.register(payload);
        showFeedback(card, result.detail || "Account created. Check your email for a verification code.");
        window.location.assign(result.redirect_url || "/verification-sent/");
      } catch (error) {
        showFeedback(card, error.message, true);
      } finally {
        button.disabled = false;
      }
    });
  }

  if (loginForm) {
    loginForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(loginForm);
      const button = loginForm.querySelector('button[type="submit"]');
      button.disabled = true;
      try {
        const result = await authApi.login(
          formData.get("username")?.toString().trim() || "",
          formData.get("password")?.toString() || "",
          formData.get("remember") === "on",
          formData.get("next")?.toString() || "",
        );
        showFeedback(card, result.detail || "A verification code has been sent to your email.");
        makeCodeForm(card, result.email, loginForm);
      } catch (error) {
        showFeedback(card, error.message, true);
      } finally {
        button.disabled = false;
      }
    });
  }

  const verificationForm = document.querySelector("[data-auth-code-form]");
  if (verificationForm) {
    const verificationCard = verificationForm.closest(".account-card");
    verificationForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(verificationForm);
      try {
        const result = await authApi.verifyEmail(
          formData.get("email")?.toString() || "",
          formData.get("code")?.toString() || "",
        );
        window.location.assign(result.redirect_url || "/login/");
      } catch (error) {
        showFeedback(verificationCard, error.message, true);
      }
    });

    verificationForm.querySelector("[data-auth-resend]")?.addEventListener(
      "click",
      async () => {
        const email = new FormData(verificationForm).get("email")?.toString() || "";
        try {
          const result = await authApi.resendCode(email);
          showFeedback(verificationCard, result.detail || "A new code has been sent.");
        } catch (error) {
          showFeedback(verificationCard, error.message, true);
        }
      },
    );
  }

  const forgotPanel = document.querySelector("[data-forgot-panel]");
  const showForgot = document.querySelector("[data-show-forgot]");
  const hideForgot = document.querySelector("[data-hide-forgot]");
  const forgotForm = document.querySelector("[data-forgot-form]");
  const logoutForm = document.querySelector("[data-auth-logout]");
  logoutForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = logoutForm.querySelector('button[type="submit"]');
    button.disabled = true;
    try {
      await authApi.logout();
      window.location.assign("/");
    } catch (error) {
      showFeedback(
        document.querySelector(".dashboard-privacy-note"),
        error.message,
        true,
      );
      button.disabled = false;
    }
  });

  const logoutOtherDevicesButton = document.querySelector(
    "[data-logout-other-devices]",
  );
  logoutOtherDevicesButton?.addEventListener("click", async () => {
    logoutOtherDevicesButton.disabled = true;
    try {
      const result = await authApi.logoutOtherDevices();
      const count = result.sessions_ended || 0;
      showFeedback(
        logoutOtherDevicesButton.closest(".dashboard-privacy-note"),
        count
          ? `Signed out of ${count} other session${count === 1 ? "" : "s"}.`
          : "No other active sessions were found.",
      );
    } catch (error) {
      showFeedback(
        logoutOtherDevicesButton.closest(".dashboard-privacy-note"),
        error.message,
        true,
      );
    } finally {
      logoutOtherDevicesButton.disabled = false;
    }
  });

  showForgot?.addEventListener("click", () => {
    forgotPanel.hidden = false;
    forgotPanel.querySelector("input").focus();
  });
  hideForgot?.addEventListener("click", () => {
    forgotPanel.hidden = true;
    showForgot.focus();
  });
  forgotForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(forgotForm);
    const button = forgotForm.querySelector('button[type="submit"]');
    button.disabled = true;
    try {
      const result = await authApi.forgotPassword(
        formData.get("email")?.toString().trim() || "",
      );
      showFeedback(card, result.detail || "If an account exists for that email, reset instructions have been sent.");
    } catch (error) {
      showFeedback(card, error.message, true);
    } finally {
      button.disabled = false;
    }
  });
})();
