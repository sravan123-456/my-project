(function () {
  "use strict";

  var modalEl = document.getElementById("imageCropModal");
  if (!modalEl || !window.bootstrap || !window.Cropper) return;

  var imageEl = document.getElementById("imageCropTarget");
  var applyBtn = document.getElementById("imageCropApply");
  var cancelBtn = document.getElementById("imageCropCancel");
  var rotateLeftBtn = document.getElementById("imageCropRotateLeft");
  var rotateRightBtn = document.getElementById("imageCropRotateRight");
  var zoomInBtn = document.getElementById("imageCropZoomIn");
  var zoomOutBtn = document.getElementById("imageCropZoomOut");
  var modal = new bootstrap.Modal(modalEl);
  var cropper = null;
  var activeInput = null;
  var objectUrl = null;

  function parseAspect(value) {
    if (!value || value === "0" || value === "free") return NaN;
    var num = parseFloat(value);
    return isNaN(num) || num <= 0 ? NaN : num;
  }

  function destroyCropper() {
    if (cropper) {
      cropper.destroy();
      cropper = null;
    }
    if (objectUrl) {
      URL.revokeObjectURL(objectUrl);
      objectUrl = null;
    }
    imageEl.src = "";
  }

  function closeModal() {
    modal.hide();
    destroyCropper();
    activeInput = null;
  }

  function showPreview(input, dataUrl) {
    var previewId = input.getAttribute("data-crop-preview");
    if (!previewId) return;
    var preview = document.querySelector(previewId);
    if (preview) {
      preview.src = dataUrl;
      preview.classList.remove("d-none");
    }
  }

  function openCropper(input, file) {
    activeInput = input;
    destroyCropper();
    objectUrl = URL.createObjectURL(file);
    imageEl.src = objectUrl;

    modalEl.addEventListener(
      "shown.bs.modal",
      function onShown() {
        modalEl.removeEventListener("shown.bs.modal", onShown);
        var aspect = parseAspect(input.getAttribute("data-crop-aspect"));
        cropper = new Cropper(imageEl, {
          aspectRatio: aspect,
          viewMode: 1,
          autoCropArea: 0.9,
          responsive: true,
          background: false,
        });
      },
      { once: true }
    );

    modal.show();
  }

  document.querySelectorAll("[data-image-crop]").forEach(function (input) {
    input.addEventListener("change", function () {
      var file = input.files && input.files[0];
      if (!file) return;

      if (!file.type || !file.type.startsWith("image/")) {
        if (input.getAttribute("data-crop-optional") === "true") {
          return;
        }
        return;
      }

      openCropper(input, file);
    });
  });

  if (rotateLeftBtn) {
    rotateLeftBtn.addEventListener("click", function () {
      if (cropper) cropper.rotate(-90);
    });
  }
  if (rotateRightBtn) {
    rotateRightBtn.addEventListener("click", function () {
      if (cropper) cropper.rotate(90);
    });
  }
  if (zoomInBtn) {
    zoomInBtn.addEventListener("click", function () {
      if (cropper) cropper.zoom(0.1);
    });
  }
  if (zoomOutBtn) {
    zoomOutBtn.addEventListener("click", function () {
      if (cropper) cropper.zoom(-0.1);
    });
  }

  if (cancelBtn) {
    cancelBtn.addEventListener("click", function () {
      if (activeInput) activeInput.value = "";
      closeModal();
    });
  }

  modalEl.addEventListener("hidden.bs.modal", function () {
    destroyCropper();
  });

  if (applyBtn) {
    applyBtn.addEventListener("click", function () {
      if (!cropper || !activeInput) return;

      var canvas = cropper.getCroppedCanvas({
        maxWidth: 2048,
        maxHeight: 2048,
        imageSmoothingEnabled: true,
        imageSmoothingQuality: "high",
      });

      if (!canvas) return;

      canvas.toBlob(
        function (blob) {
          if (!blob || !activeInput) return;
          var originalName = (activeInput.files[0] && activeInput.files[0].name) || "photo.jpg";
          var baseName = originalName.replace(/\.[^.]+$/, "") || "photo";
          var file = new File([blob], baseName + ".jpg", { type: "image/jpeg", lastModified: Date.now() });
          var transfer = new DataTransfer();
          transfer.items.add(file);
          activeInput.files = transfer.files;
          showPreview(activeInput, canvas.toDataURL("image/jpeg", 0.92));
          closeModal();
        },
        "image/jpeg",
        0.92
      );
    });
  }
})();
