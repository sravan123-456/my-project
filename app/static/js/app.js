(function () {
  "use strict";

  var loadingHtml =
    '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>';

  function mapCategory(category) {
    if (category === "danger" || category === "error") return "danger";
    if (category === "warning") return "warning";
    if (category === "info") return "info";
    return "success";
  }

  function showToast(message, category) {
    var container = document.getElementById("toastContainer");
    if (!container || !window.bootstrap) return;

    var tone = mapCategory(category);
    var toastEl = document.createElement("div");
    toastEl.className = "toast align-items-center text-bg-" + tone + " border-0";
    toastEl.setAttribute("role", "alert");
    toastEl.setAttribute("aria-live", "assertive");
    toastEl.setAttribute("aria-atomic", "true");
    toastEl.innerHTML =
      '<div class="d-flex">' +
      '<div class="toast-body">' + message + "</div>" +
      '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>' +
      "</div>";
    container.appendChild(toastEl);
    var toast = new bootstrap.Toast(toastEl, { delay: 5000 });
    toastEl.addEventListener("hidden.bs.toast", function () {
      toastEl.remove();
    });
    toast.show();
  }

  var flashEl = document.getElementById("flash-messages");
  if (flashEl) {
    try {
      JSON.parse(flashEl.textContent).forEach(function (entry) {
        showToast(entry[1], entry[0]);
      });
    } catch (e) {
      /* ignore malformed flash payload */
    }
  }

  document.querySelectorAll("form").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      var submitBtn =
        event.submitter ||
        form.querySelector(
          'button[type="submit"]:not([data-no-loading]), input[type="submit"]:not([data-no-loading])'
        );

      if (!submitBtn || submitBtn.disabled || submitBtn.hasAttribute("data-no-loading")) {
        return;
      }

      var label =
        submitBtn.dataset.loadingText ||
        (submitBtn.tagName === "INPUT" ? submitBtn.value : submitBtn.textContent.trim()) ||
        "…";

      if (form.id === "galleryUploadForm") {
        var bar = document.getElementById("galleryUploadProgress");
        var fill = document.getElementById("galleryUploadProgressBar");
        if (bar && fill) {
          bar.classList.remove("d-none");
          fill.style.width = "30%";
          var tick = 30;
          var timer = window.setInterval(function () {
            tick = Math.min(tick + 8, 92);
            fill.style.width = tick + "%";
          }, 400);
          form.dataset.uploadTimer = String(timer);
        }
      }

      window.setTimeout(function () {
        submitBtn.disabled = true;
        submitBtn.classList.add("is-loading");

        if (submitBtn.tagName === "INPUT") {
          submitBtn.dataset.originalValue = submitBtn.value;
          submitBtn.value = label;
        } else {
          submitBtn.dataset.originalHtml = submitBtn.innerHTML;
          submitBtn.innerHTML = loadingHtml + label;
        }
      }, 0);
    });
  });

  document.querySelectorAll("[data-password-toggle]").forEach(function (toggle) {
    var inputId = toggle.getAttribute("data-password-toggle");
    var input = document.getElementById(inputId);
    if (!input) return;

    toggle.addEventListener("click", function () {
      var isPassword = input.type === "password";
      input.type = isPassword ? "text" : "password";
      toggle.querySelector("i").className = isPassword ? "bi bi-eye-slash" : "bi bi-eye";
      toggle.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");
    });
  });

  document.querySelectorAll("[data-async-download]").forEach(function (link) {
    link.addEventListener("click", function () {
      var el = link;
      if (el.classList.contains("is-loading")) return;
      el.classList.add("is-loading", "disabled");
      el.dataset.originalHtml = el.innerHTML;
      var label = el.dataset.loadingText || el.textContent.trim();
      el.innerHTML = loadingHtml + label;
      window.setTimeout(function () {
        el.classList.remove("is-loading", "disabled");
        if (el.dataset.originalHtml) el.innerHTML = el.dataset.originalHtml;
      }, 8000);
    });
  });

  (function initGalleryLightbox() {
    var lightbox = document.getElementById("galleryLightbox");
    if (!lightbox) return;

    var imageEl = document.getElementById("galleryLightboxImage");
    var captionEl = document.getElementById("galleryLightboxCaption");
    var triggers = Array.prototype.slice.call(document.querySelectorAll("[data-lightbox]"));
    var index = 0;

    function showAt(i) {
      if (!triggers.length) return;
      index = (i + triggers.length) % triggers.length;
      var trigger = triggers[index];
      imageEl.src = trigger.getAttribute("data-src") || "";
      imageEl.alt = trigger.getAttribute("data-alt") || "";
      captionEl.textContent = trigger.getAttribute("data-caption") || "";
      lightbox.hidden = false;
      document.body.classList.add("lightbox-open");
    }

    function closeLightbox() {
      lightbox.hidden = true;
      imageEl.src = "";
      document.body.classList.remove("lightbox-open");
    }

    triggers.forEach(function (trigger, i) {
      trigger.addEventListener("click", function (event) {
        event.preventDefault();
        showAt(i);
      });
    });

    lightbox.querySelector(".gallery-lightbox-close").addEventListener("click", closeLightbox);
    lightbox.querySelector(".gallery-lightbox-prev").addEventListener("click", function () {
      showAt(index - 1);
    });
    lightbox.querySelector(".gallery-lightbox-next").addEventListener("click", function () {
      showAt(index + 1);
    });
    lightbox.addEventListener("click", function (event) {
      if (event.target === lightbox) closeLightbox();
    });
    document.addEventListener("keydown", function (event) {
      if (lightbox.hidden) return;
      if (event.key === "Escape") closeLightbox();
      if (event.key === "ArrowLeft") showAt(index - 1);
      if (event.key === "ArrowRight") showAt(index + 1);
    });
  })();
})();
