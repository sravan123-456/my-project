(function () {
  "use strict";

  document.querySelectorAll("[data-bulk-select]").forEach(function (root) {
    var master = root.querySelector("[data-bulk-select-all]");
    var boxes = root.querySelectorAll("[data-bulk-select-item]");
    var deleteBtn = root.querySelector("[data-bulk-delete-btn]");
    var confirmMessage = root.getAttribute("data-bulk-confirm") || "Delete selected items?";

    function selectedCount() {
      var count = 0;
      boxes.forEach(function (box) {
        if (box.checked) count += 1;
      });
      return count;
    }

    function syncMaster() {
      if (!master) return;
      var enabled = Array.prototype.filter.call(boxes, function (box) {
        return !box.disabled;
      });
      if (!enabled.length) {
        master.checked = false;
        master.indeterminate = false;
        return;
      }
      var checked = enabled.filter(function (box) {
        return box.checked;
      });
      master.checked = checked.length === enabled.length;
      master.indeterminate = checked.length > 0 && checked.length < enabled.length;
    }

    function syncDeleteButton() {
      if (!deleteBtn) return;
      deleteBtn.disabled = selectedCount() === 0;
    }

    if (master) {
      master.addEventListener("change", function () {
        boxes.forEach(function (box) {
          if (!box.disabled) box.checked = master.checked;
        });
        syncDeleteButton();
      });
    }

    boxes.forEach(function (box) {
      box.addEventListener("change", function () {
        syncMaster();
        syncDeleteButton();
      });
    });

    if (deleteBtn) {
      deleteBtn.addEventListener("click", function () {
        if (selectedCount() === 0) return;
        if (!window.confirm(confirmMessage)) return;
        var formId = deleteBtn.getAttribute("form");
        var form = formId
          ? document.getElementById(formId)
          : root.querySelector("form[data-bulk-delete-form]");
        if (form) form.submit();
      });
      syncDeleteButton();
    }

  });
})();
