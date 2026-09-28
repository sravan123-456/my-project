(function () {
  "use strict";

  if (!window.passwordResetConfig) {
    return;
  }

  var resetConfig = window.passwordResetConfig;
  var sendBtn = document.getElementById("sendResetOtpBtn");
  var resendBtn = document.getElementById("resendResetOtpBtn");
  var completeBtn = document.getElementById("completeResetBtn");
  var sendStep = document.getElementById("otpSendStep");
  var verifyStep = document.getElementById("otpVerifyStep");
  var otpInput = document.getElementById("resetOtp");
  var passwordInput = document.getElementById("resetPassword");
  var confirmInput = document.getElementById("resetPasswordConfirm");
  var errorEl = document.getElementById("resetAuthError");
  var infoEl = document.getElementById("resetAuthInfo");

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

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

  function postJson(url, payload) {
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken(),
      },
      body: JSON.stringify(payload),
    }).then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok) {
          throw new Error(data.error || "Request failed.");
        }
        return data;
      });
    });
  }

  function sendOtp(button) {
    clearError();
    setLoading(button, true, "Sending OTP…");
    postJson(resetConfig.sendUrl, {})
      .then(function () {
        sendStep.classList.add("d-none");
        verifyStep.classList.remove("d-none");
        showInfo("OTP sent to your registered mobile number.");
        if (otpInput) otpInput.focus();
      })
      .catch(function (error) {
        showError(error.message || "Could not send OTP.");
      })
      .finally(function () {
        setLoading(button, false);
      });
  }

  function completeReset() {
    clearError();
    var code = (otpInput.value || "").trim();
    var password = (passwordInput.value || "").trim();
    var confirm = (confirmInput.value || "").trim();
    if (code.length < 4) {
      showError("Enter the OTP from your SMS.");
      return;
    }
    if (password.length < 6) {
      showError("Password must be at least 6 characters.");
      return;
    }
    if (password !== confirm) {
      showError("Passwords do not match.");
      return;
    }

    setLoading(completeBtn, true, "Updating…");
    postJson(resetConfig.completeUrl, { otp: code, password: password })
      .then(function (data) {
        window.location.href = data.redirect || "/login";
      })
      .catch(function (error) {
        showError(error.message || "Could not reset password.");
      })
      .finally(function () {
        setLoading(completeBtn, false);
      });
  }

  if (sendBtn) {
    sendBtn.addEventListener("click", function () {
      sendOtp(sendBtn);
    });
  }

  if (resendBtn) {
    resendBtn.addEventListener("click", function () {
      verifyStep.classList.add("d-none");
      sendStep.classList.remove("d-none");
      if (otpInput) otpInput.value = "";
      clearError();
      sendOtp(resendBtn);
    });
  }

  if (completeBtn) {
    completeBtn.addEventListener("click", completeReset);
  }
})();
