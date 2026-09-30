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
  var widgetReady = false;

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
    button.disabled = loading || !widgetReady;
    if (loading) {
      button.dataset.originalText = button.textContent;
      button.textContent = label || "Please wait…";
    } else if (button.dataset.originalText) {
      button.textContent = button.dataset.originalText;
    }
  }

  function widgetErrorMessage(error) {
    if (!error) return "OTP request failed.";
    if (typeof error === "string") return error;
    if (error.message) return String(error.message);
    if (error.reason) return String(error.reason);
    return "OTP request failed.";
  }

  function extractAccessToken(data) {
    if (!data) return "";
    if (typeof data === "string") return data;
    return (
      data["access-token"] ||
      data.access_token ||
      data.accessToken ||
      data.token ||
      data.message ||
      ""
    );
  }

  function ensureWidgetReady() {
    if (!widgetReady || typeof window.sendOtp !== "function") {
      showError("OTP service is still loading. Please wait a moment and try again.");
      return false;
    }
    return true;
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
      return response.text().then(function (text) {
        var data = {};
        if (text) {
          try {
            data = JSON.parse(text);
          } catch (err) {
            if (!response.ok) {
              throw new Error("Request failed. Please refresh and try again.");
            }
          }
        }
        if (!response.ok) {
          throw new Error(data.error || "Request failed.");
        }
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
    if (!ensureWidgetReady()) return;
    clearError();
    setLoading(button, true, "Sending OTP…");
    window.sendOtp(
      resetConfig.identifier,
      function () {
        showVerifyStep();
        setLoading(button, false);
      },
      function (error) {
        showError(widgetErrorMessage(error));
        setLoading(button, false);
      }
    );
  }

  function resendOtp(button) {
    if (!ensureWidgetReady()) return;
    if (typeof window.retryOtp !== "function") {
      sendOtp(button);
      return;
    }
    clearError();
    setLoading(button, true, "Resending OTP…");
    window.retryOtp(
      null,
      function () {
        showInfo("OTP resent to your registered mobile number.");
        setLoading(button, false);
      },
      function (error) {
        showError(widgetErrorMessage(error));
        setLoading(button, false);
      }
    );
  }

  function completeReset() {
    if (!ensureWidgetReady()) return;

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
    if (typeof window.verifyOtp !== "function") {
      showError("OTP verification is not available. Refresh and try again.");
      return;
    }

    setLoading(completeBtn, true, "Verifying OTP…");
    window.verifyOtp(
      code,
      function (data) {
        var accessToken = extractAccessToken(data);
        if (!accessToken) {
          showError("OTP verified but no access token was returned. Try again.");
          setLoading(completeBtn, false);
          return;
        }

        setLoading(completeBtn, true, "Updating…");
        postJson(resetConfig.completeUrl, {
          access_token: accessToken,
          password: password,
        })
          .then(function (result) {
            window.location.href = result.redirect || "/login";
          })
          .catch(function (error) {
            showError(error.message || "Could not reset password.");
          })
          .finally(function () {
            setLoading(completeBtn, false);
          });
      },
      function (error) {
        showError(widgetErrorMessage(error));
        setLoading(completeBtn, false);
      }
    );
  }

  function initWidget() {
    var configuration = {
      widgetId: resetConfig.widgetId,
      tokenAuth: resetConfig.widgetToken,
      identifier: resetConfig.identifier,
      exposeMethods: true,
      captchaRenderId: "msg91Captcha",
      success: function () {},
      failure: function (error) {
        showError(widgetErrorMessage(error));
      },
    };

    function markReady() {
      widgetReady = true;
      if (sendBtn) {
        sendBtn.disabled = false;
        sendBtn.textContent = "Send OTP";
      }
    }

    function loadScript(urls, index) {
      if (index >= urls.length) {
        showError("Could not load OTP service. Refresh and try again.");
        return;
      }
      var script = document.createElement("script");
      script.src = urls[index];
      script.async = true;
      script.onload = function () {
        if (typeof window.initSendOTP === "function") {
          window.initSendOTP(configuration);
          markReady();
        } else {
          loadScript(urls, index + 1);
        }
      };
      script.onerror = function () {
        loadScript(urls, index + 1);
      };
      document.head.appendChild(script);
    }

    loadScript(
      [
        "https://verify.msg91.com/otp-provider.js",
        "https://verify.phone91.com/otp-provider.js",
      ],
      0
    );
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

  initWidget();
})();
