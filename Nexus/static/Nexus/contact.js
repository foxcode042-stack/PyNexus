(() => {
  const form = document.querySelector("[data-contact-form]");
  if (!form) return;

  const feedback = form.querySelector("[data-contact-feedback]");
  const submitButton = form.querySelector("[data-contact-submit]");
  const showFeedback = (message, isError = false) => {
    feedback.hidden = !message;
    feedback.textContent = message;
    feedback.dataset.error = String(isError);
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;

    const formData = new FormData(form);
    const enquiry = {
      full_name: String(formData.get("full_name") || "").trim(),
      email: String(formData.get("email") || "").trim(),
      phone_number: String(formData.get("phone_number") || "").trim(),
      category: String(formData.get("category") || ""),
      subject: String(formData.get("subject") || "").trim(),
      message: String(formData.get("message") || "").trim(),
    };
    const csrfToken = formData.get("csrfmiddlewaretoken");
    submitButton.disabled = true;
    submitButton.textContent = "Sending enquiry...";
    showFeedback("");

    try {
      const response = await fetch(form.dataset.contactUrl, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": String(csrfToken || ""),
        },
        body: JSON.stringify(enquiry),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || "Your message could not be sent. Please try again.");
      }
      if (typeof data.detail !== "string" || typeof data.reference !== "string") {
        throw new Error("The server returned an invalid confirmation. Please contact the academy directly.");
      }
      showFeedback(`${data.detail} Reference: ${data.reference}`);
      form.reset();
    } catch (error) {
      showFeedback(
        error instanceof Error ? error.message : "Your message could not be sent. Please try again.",
        true,
      );
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = "Send enquiry";
    }
  });
})();
