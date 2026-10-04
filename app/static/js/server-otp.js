(function (global) {
  "use strict";

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  function postJson(url, payload) {
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken(),
      },
      body: JSON.stringify(payload || {}),
    }).then(function (response) {
      return response.text().then(function (text) {
        var data = {};
        if (text) {
          try {
            data = JSON.parse(text);
          } catch (err) {
            if (!response.ok) {
              throw new Error("Could not send OTP. Please refresh and try again.");
            }
          }
        }
        if (!response.ok) {
          var error = new Error(data.error || "Could not complete OTP request.");
          error.retryAfter = data.retry_after || 0;
          throw error;
        }
        return data;
      });
    });
  }

  function startCooldown(button, seconds) {
    if (!button || !seconds) return;
    var remaining = seconds;
    button.disabled = true;
    var original = button.dataset.originalText || button.textContent;
    button.dataset.originalText = original;
    function tick() {
      if (remaining <= 0) {
        button.disabled = false;
        button.textContent = original;
        return;
      }
      button.textContent = "Wait " + remaining + "s…";
      remaining -= 1;
      window.setTimeout(tick, 1000);
    }
    tick();
  }

  global.ServerOtp = {
    send: function (phone) {
      var payload = {};
      if (phone) payload.phone = phone;
      return postJson("/otp/send", payload);
    },
    verify: function (phone, otp) {
      var payload = { otp: otp };
      if (phone) payload.phone = phone;
      return postJson("/otp/verify", payload);
    },
    resend: function (phone) {
      var payload = {};
      if (phone) payload.phone = phone;
      return postJson("/otp/resend", payload);
    },
    startCooldown: startCooldown,
  };
})(window);
