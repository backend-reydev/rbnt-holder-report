// Light or dark mode, chart tooltips, and the Table buttons on charts.
(function () {
  var html = document.documentElement;
  var toggle = document.getElementById("mode");

  function dark() {
    var set = html.dataset.mode;
    if (set) return set === "dark";
    return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  }
  function caption() { if (toggle) toggle.textContent = dark() ? "Light" : "Dark"; }
  if (toggle) {
    caption();
    toggle.addEventListener("click", function () {
      html.dataset.mode = dark() ? "light" : "dark";
      try { localStorage.setItem("holders-mode", html.dataset.mode); } catch (err) { /* storage blocked */ }
      caption();
    });
  }

  var bubble = document.createElement("div");
  bubble.id = "tip";
  bubble.setAttribute("role", "status");
  document.body.appendChild(bubble);
  function place(target, x, y) {
    bubble.textContent = target.getAttribute("data-tip");
    bubble.classList.add("show");
    var w = bubble.offsetWidth, h = bubble.offsetHeight;
    bubble.style.left = Math.max(8, Math.min(x + 12, innerWidth - w - 8)) + "px";
    bubble.style.top = (y - h - 14 < 8 ? y + 18 : y - h - 14) + "px";
  }
  function find(el) { return el && el.closest ? el.closest("[data-tip]") : null; }
  document.addEventListener("pointermove", function (e) {
    var t = find(e.target);
    if (t) place(t, e.clientX, e.clientY); else bubble.classList.remove("show");
  });
  document.addEventListener("focusin", function (e) {
    var t = find(e.target);
    if (!t) return;
    var box = t.getBoundingClientRect();
    place(t, box.left + box.width / 2, box.top);
  });
  document.addEventListener("focusout", function () { bubble.classList.remove("show"); });
  addEventListener("scroll", function () { bubble.classList.remove("show"); }, { passive: true });

  document.querySelectorAll("[data-toggle]").forEach(function (btn) {
    btn.setAttribute("aria-pressed", "false");
    btn.addEventListener("click", function () {
      var panel = btn.closest(".chart").querySelector(".as-table");
      var open = panel.hasAttribute("hidden");
      if (open) panel.removeAttribute("hidden"); else panel.setAttribute("hidden", "");
      btn.setAttribute("aria-pressed", open ? "true" : "false");
    });
  });
})();
