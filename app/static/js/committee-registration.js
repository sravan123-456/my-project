(function () {
  "use strict";

  if (!window.committeeRegistrationConfig || !window.Msg91Registration) {
    return;
  }

  var cfg = window.committeeRegistrationConfig;
  var form = document.querySelector(".pricing-register-form");
  var submitBtn = document.getElementById("committeeSubmitBtn");
  var otpSection = document.getElementById("committeeOtpSection");
  var otpInput = document.getElementById("committeeOtpInput");
  var resendBtn = document.getElementById("committeeResendOtpBtn");
  var tokenInput = document.getElementById("committeePhoneAccessToken");
  var errorEl = document.getElementById("committeeAuthError");
  var infoEl = document.getElementById("committeeAuthInfo");
  var phoneInput = document.getElementById("committeePhone");
  var widget = new window.Msg91Registration(cfg);

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
    button.disabled = loading;
    if (loading) {
      button.dataset.originalText = button.textContent;
      button.textContent = label || "Please wait…";
    } else if (button.dataset.originalText) {
      button.textContent = button.dataset.originalText;
    }
  }

  function showOtpStep() {
    if (otpSection) otpSection.classList.remove("d-none");
    if (otpInput) otpInput.focus();
  }

  widget.init();

  widget.config.onReady = function () {
    if (submitBtn) {
      submitBtn.disabled = false;
    }
  };

  widget.config.onError = showError;

  if (resendBtn) {
    resendBtn.addEventListener("click", function () {
      clearError();
      setLoading(resendBtn, true, "Resending…");
      widget.resendOtp({
        onSuccess: function () {
          showInfo(cfg.otpSentLabel || "OTP resent.");
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
      clearError();
      if (!form.reportValidity()) {
        return;
      }

      if (!widget.otpSent) {
        setLoading(submitBtn, true, "Sending OTP…");
        widget.sendOtp(phoneInput ? phoneInput.value : "", {
          onSuccess: function () {
            showInfo(cfg.otpSentLabel || "OTP sent to your phone.");
            showOtpStep();
            setLoading(submitBtn, false);
            if (submitBtn.dataset.originalText) {
              submitBtn.textContent = cfg.verifyLabel || "Verify phone & register";
            }
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
          setLoading(submitBtn, true, "Registering…");
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
