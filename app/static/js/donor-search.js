(function () {
  "use strict";

  var MIN_CHARS = 2;
  var DEBOUNCE_MS = 280;

  function debounce(fn, wait) {
    var timer;
    return function () {
      var args = arguments;
      var context = this;
      clearTimeout(timer);
      timer = setTimeout(function () {
        fn.apply(context, args);
      }, wait);
    };
  }

  function hideSuggestions(listEl) {
    listEl.hidden = true;
    listEl.innerHTML = "";
  }

  function showSuggestions(input, listEl, names) {
    listEl.innerHTML = "";
    if (!names.length) {
      hideSuggestions(listEl);
      return;
    }

    names.forEach(function (name) {
      var item = document.createElement("li");
      item.setAttribute("role", "option");
      var button = document.createElement("button");
      button.type = "button";
      button.className = "donor-search-suggestion-item";
      button.textContent = name;
      button.addEventListener("click", function () {
        input.value = name;
        hideSuggestions(listEl);
        var form = input.closest("form");
        if (form) {
          form.requestSubmit();
        }
      });
      item.appendChild(button);
      listEl.appendChild(item);
    });
    listEl.hidden = false;
  }

  function initDonorSearch(input) {
    var wrap = input.closest(".donor-search-wrap");
    if (!wrap) {
      return;
    }
    var listEl = wrap.querySelector(".donor-search-suggestions");
    if (!listEl) {
      return;
    }

    var suggestionsUrl = input.getAttribute("data-suggestions-url");
    if (!suggestionsUrl) {
      return;
    }

    var activeController = null;

    function fetchSuggestions(query) {
      if (activeController) {
        activeController.abort();
      }
      activeController = new AbortController();

      var url = suggestionsUrl + "?q=" + encodeURIComponent(query);
      fetch(url, {
        credentials: "same-origin",
        signal: activeController.signal,
      })
        .then(function (response) {
          if (!response.ok) {
            throw new Error("suggestions failed");
          }
          return response.json();
        })
        .then(function (data) {
          showSuggestions(input, listEl, data.results || []);
        })
        .catch(function (err) {
          if (err.name !== "AbortError") {
            hideSuggestions(listEl);
          }
        });
    }

    var onInput = debounce(function () {
      var query = input.value.trim();
      if (query.length < MIN_CHARS) {
        hideSuggestions(listEl);
        return;
      }
      fetchSuggestions(query);
    }, DEBOUNCE_MS);

    input.addEventListener("input", onInput);
    input.addEventListener("focus", function () {
      var query = input.value.trim();
      if (query.length >= MIN_CHARS) {
        fetchSuggestions(query);
      }
    });
    input.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        hideSuggestions(listEl);
      }
    });
    document.addEventListener("click", function (event) {
      if (!wrap.contains(event.target)) {
        hideSuggestions(listEl);
      }
    });
  }

  document.querySelectorAll("[data-donor-search-autocomplete]").forEach(initDonorSearch);
})();
