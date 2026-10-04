(function () {
  "use strict";

  var steps = {
    choice: document.getElementById("landingChoiceStep"),
    "existing-join": document.getElementById("landingExistingJoinStep"),
    "existing-login": document.getElementById("landingExistingLoginStep"),
  };
  var backBtn = document.getElementById("landingBackBtn");
  var hash = (window.location.hash || "").replace("#", "");
  var initialView = document.body.getAttribute("data-landing-view") || "choice";
  var viewParam = new URLSearchParams(window.location.search).get("view");
  if (viewParam && steps[viewParam]) {
    initialView = viewParam;
  }
  if (hash === "existing-committee" || hash === "join") {
    initialView = "existing-join";
  } else if (hash === "login" || hash === "committee") {
    initialView = "existing-login";
  } else if (hash === "new-committee" || hash === "new") {
    window.location.href = "/pricing";
    return;
  }

  var landingCard = document.querySelector(".landing-card");

  function showStep(view) {
    Object.keys(steps).forEach(function (key) {
      if (!steps[key]) return;
      steps[key].classList.toggle("active", key === view);
    });
    if (backBtn) {
      backBtn.classList.toggle("d-none", view === "choice");
    }
    document.body.setAttribute("data-landing-view", view);
    if (landingCard) {
      landingCard.scrollTop = 0;
    }
    document.dispatchEvent(
      new CustomEvent("landing-step-change", { detail: { view: view } })
    );
  }

  document.querySelectorAll("[data-landing-go]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      showStep(btn.getAttribute("data-landing-go"));
    });
  });

  if (backBtn) {
    backBtn.addEventListener("click", function () {
      var current = document.body.getAttribute("data-landing-view");
      if (current === "existing-login") {
        showStep("existing-join");
        return;
      }
      showStep("choice");
      if (window.history.replaceState) {
        window.history.replaceState(null, "", window.location.pathname);
      }
    });
  }

  document.querySelectorAll('[data-landing-go="choice"]').forEach(function (btn) {
    btn.addEventListener("click", function () {
      if (window.history.replaceState) {
        window.history.replaceState(null, "", window.location.pathname);
      }
    });
  });

  var joinForm = document.getElementById("joinAccountForm");
  if (joinForm) {
    joinForm.addEventListener("submit", function () {
      var password = document.getElementById("joinPassword");
      var confirm = document.getElementById("joinConfirmPassword");
      if (password && confirm) {
        confirm.value = password.value;
      }
    });
  }

  showStep(initialView);
})();
