(function (global) {
  "use strict";

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

  function widgetErrorMessage(error) {
    if (!error) return "OTP request failed.";
    if (typeof error === "string") return error;
    if (error.message) return String(error.message);
    if (error.reason) return String(error.reason);
    return "OTP request failed.";
  }

  function normalizePhoneIdentifier(value) {
    var digits = String(value || "").replace(/\D/g, "");
    if (digits.length === 10) return "91" + digits;
    if (digits.length === 12 && digits.indexOf("91") === 0) return digits;
    return "";
  }

  function Msg91Registration(config) {
    this.config = config || {};
    this.widgetReady = false;
    this.accessToken = "";
    this.otpSent = false;
  }

  Msg91Registration.prototype.init = function () {
    var self = this;
    var configuration = {
      widgetId: this.config.widgetId,
      tokenAuth: this.config.widgetToken,
      exposeMethods: true,
      captchaRenderId: this.config.captchaId || "msg91Captcha",
      success: function () {},
      failure: function (error) {
        if (self.config.onError) self.config.onError(widgetErrorMessage(error));
      },
    };

    function loadScript(urls, index) {
      if (index >= urls.length) {
        if (self.config.onError) {
          self.config.onError("Could not load OTP service. Refresh and try again.");
        }
        return;
      }
      var script = document.createElement("script");
      script.src = urls[index];
      script.async = true;
      script.onload = function () {
        if (typeof global.initSendOTP === "function") {
          global.initSendOTP(configuration);
          self.widgetReady = true;
          if (self.config.onReady) self.config.onReady();
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
  };

  Msg91Registration.prototype.sendOtp = function (phoneValue, callbacks) {
    var self = this;
    if (!this.widgetReady || typeof global.sendOtp !== "function") {
      callbacks.onError("OTP service is still loading. Please wait.");
      return;
    }
    var identifier = normalizePhoneIdentifier(phoneValue);
    if (!identifier) {
      callbacks.onError("Enter a valid 10-digit Indian mobile number.");
      return;
    }
    global.sendOtp(
      identifier,
      function () {
        self.otpSent = true;
        callbacks.onSuccess();
      },
      function (error) {
        callbacks.onError(widgetErrorMessage(error));
      }
    );
  };

  Msg91Registration.prototype.resendOtp = function (callbacks) {
    if (!this.widgetReady) {
      callbacks.onError("OTP service is still loading. Please wait.");
      return;
    }
    if (typeof global.retryOtp !== "function") {
      callbacks.onError("Resend is not available right now.");
      return;
    }
    global.retryOtp(
      null,
      function () {
        callbacks.onSuccess();
      },
      function (error) {
        callbacks.onError(widgetErrorMessage(error));
      }
    );
  };

  Msg91Registration.prototype.verifyOtp = function (otpValue, callbacks) {
    var self = this;
    if (!this.widgetReady || typeof global.verifyOtp !== "function") {
      callbacks.onError("OTP service is still loading. Please wait.");
      return;
    }
    var code = String(otpValue || "").trim();
    if (code.length < 4) {
      callbacks.onError("Enter the OTP from your SMS.");
      return;
    }
    global.verifyOtp(
      code,
      function (data) {
        var token = extractAccessToken(data);
        if (!token) {
          callbacks.onError("OTP verified but no access token was returned.");
          return;
        }
        self.accessToken = token;
        callbacks.onSuccess(token);
      },
      function (error) {
        callbacks.onError(widgetErrorMessage(error));
      }
    );
  };

  global.Msg91Registration = Msg91Registration;
})(window);
