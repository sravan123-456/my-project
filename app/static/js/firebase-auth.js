(function () {
  "use strict";

  if (!window.firebase || !window.firebaseClientConfig || !window.firebaseClientConfig.apiKey) {
    return;
  }

  var config = window.firebaseClientConfig;
  var verifyUrl = window.firebaseVerifyUrl;
  var auth = null;
  var recaptchaVerifier = null;
  var confirmationResult = null;

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  function showError(message) {
    var el = document.getElementById("landingAuthError");
    if (!el) return;
    el.textContent = message;
    el.classList.remove("d-none");
  }

  function clearError() {
    var el = document.getElementById("landingAuthError");
    if (el) {
      el.textContent = "";
      el.classList.add("d-none");
    }
  }

  function showInfo(message) {
    var el = document.getElementById("landingAuthInfo");
    if (!el) return;
    el.textContent = message;
    el.classList.remove("d-none");
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

  function postVerify(idToken) {
    return fetch(verifyUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken(),
      },
      body: JSON.stringify({ idToken: idToken }),
    }).then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok) {
          throw new Error(data.error || "Login failed.");
        }
        return data;
      });
    });
  }

  function finishLogin(idToken) {
    return postVerify(idToken).then(function (data) {
      window.location.href = data.redirect || "/dashboard";
    });
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

  function bindPhoneFlow() {
    var phoneInput = document.getElementById("landingPhone");
    var sendBtn = document.getElementById("sendOtpBtn");
    var verifyBtn = document.getElementById("verifyOtpBtn");
    var otpInput = document.getElementById("landingOtp");
    var changePhoneBtn = document.getElementById("changePhoneBtn");
    var phoneStep = document.getElementById("phoneLoginStep");
    var otpStep = document.getElementById("otpLoginStep");

    if (!phoneInput || !sendBtn) return;

    phoneInput.addEventListener("input", function () {
      phoneInput.value = phoneInput.value.replace(/\D/g, "").slice(0, 10);
      sendBtn.disabled = phoneInput.value.length !== 10;
      clearError();
    });

    sendBtn.addEventListener("click", function () {
      clearError();
      var phone = "+91" + phoneInput.value;
      setLoading(sendBtn, true, "Sending OTP…");
      initRecaptcha()
        .verify()
        .then(function () {
          return auth.signInWithPhoneNumber(phone, recaptchaVerifier);
        })
        .then(function (result) {
          confirmationResult = result;
          phoneStep.classList.add("d-none");
          otpStep.classList.remove("d-none");
          showInfo("OTP sent to " + phone);
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
          setLoading(sendBtn, false);
        });
    });

    if (verifyBtn) {
      verifyBtn.addEventListener("click", function () {
        clearError();
        if (!confirmationResult) {
          showError("Please request an OTP first.");
          return;
        }
        var code = (otpInput.value || "").trim();
        if (code.length < 6) {
          showError("Enter the 6-digit OTP.");
          return;
        }
        setLoading(verifyBtn, true, "Verifying…");
        confirmationResult
          .confirm(code)
          .then(function (result) {
            return result.user.getIdToken();
          })
          .then(finishLogin)
          .catch(function (error) {
            showError(error.message || "Invalid OTP.");
          })
          .finally(function () {
            setLoading(verifyBtn, false);
          });
      });
    }

    if (changePhoneBtn) {
      changePhoneBtn.addEventListener("click", function () {
        otpStep.classList.add("d-none");
        phoneStep.classList.remove("d-none");
        confirmationResult = null;
        if (otpInput) otpInput.value = "";
        clearError();
      });
    }
  }

  function bindGoogleFlow() {
    var googleBtn = document.getElementById("googleSignInBtn");
    if (!googleBtn) return;

    googleBtn.addEventListener("click", function () {
      clearError();
      setLoading(googleBtn, true, "Signing in…");
      var provider = new firebase.auth.GoogleAuthProvider();
      auth
        .signInWithPopup(provider)
        .then(function (result) {
          return result.user.getIdToken();
        })
        .then(finishLogin)
        .catch(function (error) {
          if (error.code !== "auth/popup-closed-by-user") {
            showError(error.message || "Google sign-in failed.");
          }
        })
        .finally(function () {
          setLoading(googleBtn, false);
        });
    });
  }

  initFirebase();
  bindPhoneFlow();
  bindGoogleFlow();
})();
