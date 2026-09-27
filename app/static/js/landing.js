(function () {
  "use strict";

  var toggleBtn = document.getElementById("toggleCommitteeLogin");
  var panel = document.getElementById("committeeLoginPanel");
  if (!toggleBtn || !panel) return;

  var showLabel = toggleBtn.dataset.showLabel || toggleBtn.textContent;
  var hideLabel = toggleBtn.dataset.hideLabel || "Hide committee login";

  toggleBtn.addEventListener("click", function () {
    panel.classList.toggle("show");
    toggleBtn.textContent = panel.classList.contains("show") ? hideLabel : showLabel;
  });

  if (window.location.hash === "#committee" || panel.classList.contains("show")) {
    panel.classList.add("show");
  }
})();
