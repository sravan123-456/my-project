(function () {
  "use strict";

  if (!window.joinRegistrationConfig || !window.Msg91Registration) {
    return;
  }

  var cfg = window.joinRegistrationConfig;
  var form = document.getElementById("joinAccountForm");
  var submitBtn = document.getElementById("joinSubmitBtn");
  var joinStep = document.getElementById("landingExistingJoinStep");
  var otpSection = document.getElementById("joinOtpSection");
  var otpInput = document.getElementById("joinOtpInput");
  var resendBtn = document.getElementById("joinResendOtpBtn");
  var tokenInput = document.getElementById("joinPhoneAccessToken");
  var errorEl = document.getElementById("joinAuthError");
  var infoEl = document.getElementById("joinAuthInfo");
  var phoneInput = document.getElementById("joinPhone");
  var passwordInput = document.getElementById("joinPassword");
  var confirmInput = document.getElementById("joinConfirmPassword");
  var widget = new window.Msg91Registration(cfg);
  var isSubmitting = false;
  var resendCooldown = 0;

  widget.config.onReady = function () {
    if (submitBtn) submitBtn.disabled = false;
  };

  widget.config.onError = function (message) {
    showError(message);
    if (submitBtn) submitBtn.disabled = false;
  };

  function showError(message) {
    if (!errorEl) return;
    errorEl.textContent = message;
    errorEl.classList.remove("d-none");
  }

  function clearError() {
    if (errorEl) {
      errorEl.textContent = "";
      errorEl.classList.add("d-none");
    }
  }

  function showInfo(message) {
    if (!infoEl) return;
    infoEl.textContent = message;
    infoEl.classList.remove("d-none");
  }

  function setLoading(button, loading, label) {
    if (!button) return;
    button.disabled = !!loading;
    if (loading) {
      button.dataset.originalText = button.textContent;
      button.textContent = label || "Please wait…";
    } else if (button.dataset.originalText) {
      button.textContent = button.dataset.originalText;
    }
  }

  function syncPasswordConfirm() {
    if (passwordInput && confirmInput) {
      confirmInput.value = passwordInput.value;
      confirmInput.removeAttribute("required");
    }
  }

  function fieldIsHidden(field) {
    if (field.classList.contains("d-none") || field.type === "hidden") return true;
    return !!field.closest(".d-none");
  }

  function validateJoinForm() {
    syncPasswordConfirm();
    var firstInvalid = null;
    form.querySelectorAll("input, select, textarea").forEach(function (field) {
      if (fieldIsHidden(field)) {
        field.removeAttribute("required");
        return;
      }
      if (field.type === "email" && !field.value.trim()) {
        field.removeAttribute("required");
        return;
      }
      if (!field.checkValidity() && !firstInvalid) firstInvalid = field;
    });
    if (firstInvalid) {
      showError(firstInvalid.validationMessage || "Please fill in all required fields.");
      firstInvalid.focus();
      return false;
    }
    return true;
  }

  function showOtpStep() {
    if (otpSection) otpSection.classList.remove("d-none");
    if (otpInput) otpInput.focus();
  }

  function ensureWidgetInit() {
    if (!joinStep || !joinStep.classList.contains("active")) return;
    if (!widget.initialized) widget.init();
  }

  function resetJoinFlow() {
    clearError();
    if (infoEl) {
      infoEl.textContent = "";
      infoEl.classList.add("d-none");
    }
    if (tokenInput) tokenInput.value = "";
    if (otpInput) otpInput.value = "";
    if (otpSection) otpSection.classList.add("d-none");
    widget.otpSent = false;
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = cfg.submitLabel || "Create account";
    }
  }

  document.addEventListener("landing-step-change", function (event) {
    if (!event.detail) return;
    if (event.detail.view === "existing-join") {
      setTimeout(ensureWidgetInit, 100);
    } else if (event.detail.view === "choice") {
      resetJoinFlow();
    }
  });

  document.querySelectorAll('[data-landing-go="existing-join"]').forEach(function (btn) {
    btn.addEventListener("click", function () {
      setTimeout(ensureWidgetInit, 100);
    });
  });

  if (document.body.getAttribute("data-landing-view") === "existing-join") {
    ensureWidgetInit();
  }

  if (passwordInput) passwordInput.addEventListener("input", syncPasswordConfirm);

  if (resendBtn) {
    resendBtn.addEventListener("click", function () {
      if (resendCooldown > 0) return;
      clearError();
      setLoading(resendBtn, true, "Resending…");
      widget.resendOtp({
        onSuccess: function () {
          showInfo(cfg.otpSentLabel || "OTP resent.");
          resendCooldown = 45;
          setLoading(resendBtn, false);
        },
        onError: function (message) {
          showError(message);
          setLoading(resendBtn, false);
        },
      });
    });
  }

  if (submitBtn && form) {
    submitBtn.addEventListener("click", function () {
      if (isSubmitting) return;
      clearError();
      syncPasswordConfirm();
      if (!validateJoinForm()) return;

      ensureWidgetInit();

      if (!widget.otpSent) {
        setLoading(submitBtn, true, "Sending OTP…");
        widget.sendOtp(phoneInput ? phoneInput.value : "", {
          onSuccess: function () {
            showInfo(cfg.otpSentLabel || "OTP sent. Check your SMS.");
            showOtpStep();
            setLoading(submitBtn, false);
            submitBtn.textContent = cfg.verifyLabel || "Verify phone & create account";
          },
          onError: function (message) {
            showError(message);
            setLoading(submitBtn, false);
          },
        });
        return;
      }

      setLoading(submitBtn, true, "Verifying…");
      widget.verifyOtp(otpInput ? otpInput.value : "", {
        onSuccess: function (token) {
          if (tokenInput) tokenInput.value = token;
          syncPasswordConfirm();
          isSubmitting = true;
          setLoading(submitBtn, true, "Creating account…");
          form.submit();
        },
        onError: function (message) {
          showError(message);
          setLoading(submitBtn, false);
        },
      });
    });
  }
})();
