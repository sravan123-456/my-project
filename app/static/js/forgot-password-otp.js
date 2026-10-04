(function () {
  "use strict";

  if (!window.passwordResetConfig || !window.Msg91Registration) {
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
  var widget = new window.Msg91Registration(resetConfig);

  widget.config.onReady = function () {
    if (sendBtn) {
      sendBtn.disabled = false;
      sendBtn.textContent = "Send OTP";
    }
  };

  widget.config.onError = showError;

  widget.init();

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

  function postJson(url, payload) {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": meta ? meta.getAttribute("content") : "",
      },
      body: JSON.stringify(payload),
    }).then(function (response) {
      return response.text().then(function (text) {
        var data = {};
        if (text) {
          try {
            data = JSON.parse(text);
          } catch (err) {
            if (!response.ok) throw new Error("Request failed. Please refresh and try again.");
          }
        }
        if (!response.ok) throw new Error(data.error || "Request failed.");
        return data;
      });
    });
  }

  function showVerifyStep() {
    sendStep.classList.add("d-none");
    verifyStep.classList.remove("d-none");
    showInfo("OTP sent to your registered mobile number.");
    if (otpInput) otpInput.focus();
  }

  function sendOtp(button) {
    clearError();
    setLoading(button, true, "Sending OTP…");
    widget.sendOtp(resetConfig.identifier, {
      onSuccess: function () {
        showVerifyStep();
        setLoading(button, false);
      },
      onError: function (message) {
        showError(message);
        setLoading(button, false);
      },
    });
  }

  function resendOtp(button) {
    clearError();
    setLoading(button, true, "Resending…");
    widget.resendOtp({
      onSuccess: function () {
        showInfo("OTP resent to your registered mobile number.");
        setLoading(button, false);
      },
      onError: function (message) {
        showError(message);
        setLoading(button, false);
      },
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

    setLoading(completeBtn, true, "Verifying OTP…");
    widget.verifyOtp(code, {
      onSuccess: function (token) {
        setLoading(completeBtn, true, "Updating…");
        postJson(resetConfig.completeUrl, {
          access_token: token,
          password: password,
        })
          .then(function (result) {
            window.location.href = result.redirect || "/login";
          })
          .catch(function (error) {
            showError(error.message || "Could not reset password.");
            setLoading(completeBtn, false);
          });
      },
      onError: function (message) {
        showError(message);
        setLoading(completeBtn, false);
      },
    });
  }

  if (sendBtn) {
    sendBtn.addEventListener("click", function () {
      sendOtp(sendBtn);
    });
  }

  if (resendBtn) {
    resendBtn.addEventListener("click", function () {
      resendOtp(resendBtn);
    });
  }

  if (completeBtn) {
    completeBtn.addEventListener("click", completeReset);
  }
})();
