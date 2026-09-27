(function () {
  "use strict";

  if (!window.firebase || !window.firebaseClientConfig || !window.passwordResetConfig) {
    return;
  }

  var config = window.firebaseClientConfig;
  var resetConfig = window.passwordResetConfig;
  var auth = null;
  var recaptchaVerifier = null;
  var confirmationResult = null;

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

  function initRecaptcha() {
    if (recaptchaVerifier) {
      return recaptchaVerifier;
    }
    recaptchaVerifier = new firebase.auth.RecaptchaVerifier("firebase-recaptcha", {
      size: "invisible",
      callback: function () {},
    });
    return recaptchaVerifier;
  }

  function initFirebase() {
    if (!firebase.apps.length) {
      firebase.initializeApp(config);
    }
    auth = firebase.auth();
    auth.useDeviceLanguage();
  }

  function sendOtp(button) {
    clearError();
    setLoading(button, true, "Sending OTP…");
    initRecaptcha()
      .verify()
      .then(function () {
        return auth.signInWithPhoneNumber(resetConfig.phone, recaptchaVerifier);
      })
      .then(function (result) {
        confirmationResult = result;
        sendStep.classList.add("d-none");
        verifyStep.classList.remove("d-none");
        showInfo("OTP sent to your registered mobile number.");
        if (otpInput) otpInput.focus();
      })
      .catch(function (error) {
        showError(error.message || "Could not send OTP.");
        if (recaptchaVerifier) {
          recaptchaVerifier.clear();
          recaptchaVerifier = null;
        }
      })
      .finally(function () {
        setLoading(button, false);
      });
  }

  function completeReset() {
    clearError();
    if (!confirmationResult) {
      showError("Please request an OTP first.");
      return;
    }
    var code = (otpInput.value || "").trim();
    var password = (passwordInput.value || "").trim();
    var confirm = (confirmInput.value || "").trim();
    if (code.length < 6) {
      showError("Enter the 6-digit OTP.");
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
    confirmationResult
      .confirm(code)
      .then(function (result) {
        return result.user.getIdToken();
      })
      .then(function (idToken) {
        return fetch(resetConfig.completeUrl, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken(),
          },
          body: JSON.stringify({ idToken: idToken, password: password }),
        }).then(function (response) {
          return response.json().then(function (data) {
            if (!response.ok) {
              throw new Error(data.error || "Could not reset password.");
            }
            return data;
          });
        });
      })
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

  initFirebase();

  if (sendBtn) {
    sendBtn.addEventListener("click", function () {
      sendOtp(sendBtn);
    });
  }

  if (resendBtn) {
    resendBtn.addEventListener("click", function () {
      verifyStep.classList.add("d-none");
      sendStep.classList.remove("d-none");
      confirmationResult = null;
      if (otpInput) otpInput.value = "";
      clearError();
      sendOtp(resendBtn);
    });
  }

  if (completeBtn) {
    completeBtn.addEventListener("click", completeReset);
  }
})();
