(function () {
  "use strict";

  if (!window.findCommitteeConfig || !window.Msg91Registration) {
    return;
  }

  var config = window.findCommitteeConfig;
  var sendBtn = document.getElementById("sendFindOtpBtn");
  var resendBtn = document.getElementById("resendFindOtpBtn");
  var completeBtn = document.getElementById("completeFindBtn");
  var sendStep = document.getElementById("otpSendStep");
  var verifyStep = document.getElementById("otpVerifyStep");
  var resultsEl = document.getElementById("committeeResults");
  var listEl = document.getElementById("committeeList");
  var otpInput = document.getElementById("findOtp");
  var errorEl = document.getElementById("findCommitteeError");
  var infoEl = document.getElementById("findCommitteeInfo");
  var widget = new window.Msg91Registration(config);

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
    showInfo("OTP sent to your mobile number.");
    if (otpInput) otpInput.focus();
  }

  function sendOtp(button) {
    clearError();
    setLoading(button, true, "Sending OTP…");
    widget.sendOtp(config.identifier, {
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
        showInfo("OTP resent to your mobile number.");
        setLoading(button, false);
      },
      onError: function (message) {
        showError(message);
        setLoading(button, false);
      },
    });
  }

  function renderResults(committees) {
    if (!listEl || !resultsEl) return;
    listEl.innerHTML = "";
    committees.forEach(function (item) {
      var card = document.createElement("div");
      card.className = "border rounded p-3 bg-light";

      var title = document.createElement("div");
      title.className = "fw-semibold";
      title.textContent = item.committee_name || item.committee_code;

      var code = document.createElement("div");
      code.className = "small text-muted mb-2";
      code.textContent = "Committee code: " + item.committee_code;

      var user = document.createElement("div");
      user.className = "small mb-2";
      user.textContent = "Username: " + item.username;

      var link = document.createElement("a");
      link.className = "btn btn-sm btn-festival";
      link.href =
        config.loginUrl +
        "?org=" +
        encodeURIComponent(item.committee_code) +
        "#login";
      link.textContent = "Go to Login";

      card.appendChild(title);
      card.appendChild(code);
      card.appendChild(user);
      card.appendChild(link);
      listEl.appendChild(card);
    });

    verifyStep.classList.add("d-none");
    resultsEl.classList.remove("d-none");
    showInfo("Use the committee code and your username to log in.");
  }

  function completeLookup() {
    clearError();
    var code = (otpInput.value || "").trim();
    if (code.length < 4) {
      showError("Enter the OTP from your SMS.");
      return;
    }

    setLoading(completeBtn, true, "Verifying OTP…");
    widget.verifyOtp(code, {
      onSuccess: function (token) {
        setLoading(completeBtn, true, "Looking up…");
        postJson(config.completeUrl, { access_token: token })
          .then(function (result) {
            renderResults(result.committees || []);
            setLoading(completeBtn, false);
          })
          .catch(function (error) {
            showError(error.message || "Could not find your committee.");
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
    completeBtn.addEventListener("click", completeLookup);
  }
})();
