(function () {
  // Theme: remembered per viewer when storage is available, system default otherwise.
  var root = document.documentElement;
  try {
    var saved = localStorage.getItem("rbnt-theme");
    if (saved === "light" || saved === "dark") root.setAttribute("data-theme", saved);
  } catch (e) {}
  var btn = document.getElementById("theme");
  function isDark() {
    var t = root.getAttribute("data-theme");
    if (t) return t === "dark";
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }
  function label() { if (btn) btn.textContent = isDark() ? "Light theme" : "Dark theme"; }
  if (btn) {
    label();
    btn.addEventListener("click", function () {
      var next = isDark() ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("rbnt-theme", next); } catch (e) {}
      label();
    });
  }

  // Tooltip for every chart mark that carries data-tip.
  var tip = document.createElement("div");
  tip.id = "tip";
  tip.setAttribute("role", "status");
  document.body.appendChild(tip);
  function show(el, x, y) {
    tip.textContent = el.getAttribute("data-tip");
    tip.classList.add("on");
    var w = tip.offsetWidth, h = tip.offsetHeight;
    var left = Math.min(x + 14, window.innerWidth - w - 8);
    var top = y - h - 12 < 8 ? y + 16 : y - h - 12;
    tip.style.left = Math.max(8, left) + "px";
    tip.style.top = top + "px";
  }
  function hide() { tip.classList.remove("on"); }
  document.addEventListener("mousemove", function (e) {
    var el = e.target.closest && e.target.closest("[data-tip]");
    if (el) show(el, e.clientX, e.clientY); else hide();
  });
  document.addEventListener("focusin", function (e) {
    var el = e.target.closest && e.target.closest("[data-tip]");
    if (!el) return;
    var r = el.getBoundingClientRect();
    show(el, r.left + r.width / 2, r.top);
  });
  document.addEventListener("focusout", hide);
  document.addEventListener("scroll", hide, { passive: true });

  // Highlight the section in view in the contents rail.
  var links = Array.prototype.slice.call(document.querySelectorAll(".toc a"));
  if ("IntersectionObserver" in window && links.length) {
    var map = {};
    links.forEach(function (a) { map[a.getAttribute("href").slice(1)] = a; });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting && map[en.target.id]) {
          links.forEach(function (a) { a.classList.remove("on"); });
          map[en.target.id].classList.add("on");
        }
      });
    }, { rootMargin: "-20% 0px -70% 0px" });
    Object.keys(map).forEach(function (id) { var s = document.getElementById(id); if (s) io.observe(s); });
  }

  // Open every table view before printing, so the PDF from the browser is complete.
  window.addEventListener("beforeprint", function () {
    document.querySelectorAll("details.tv").forEach(function (d) { d.setAttribute("open", ""); });
  });
})();
