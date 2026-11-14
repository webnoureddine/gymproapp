/* GymPro DZ — small helpers, no framework */
(function () {
  "use strict";

  // ---------- theme
  window.toggleTheme = function () {
    var d = document.documentElement;
    var t = d.dataset.theme === "dark" ? "light" : "dark";
    d.dataset.theme = t;
    try { localStorage.setItem("theme", t); } catch (e) {}
    if (window.Chart) location.reload();
  };

  // ---------- money format
  window.money = function (v) {
    var n = Number(v || 0);
    var s = n.toLocaleString("fr-FR", { minimumFractionDigits: n % 1 ? 2 : 0, maximumFractionDigits: 2 });
    return "\u2066" + s + "\u00a0" + (GYM.currency || "DA") + "\u2069";
  };

  // ---------- flash messages fade out
  var msgs = document.getElementById("messages");
  if (msgs) setTimeout(function () { msgs.style.transition = "opacity .5s"; msgs.style.opacity = 0; setTimeout(function () { msgs.remove(); }, 600); }, 5000);

  // ---------- modals: <button data-modal="id">, <div class="modal" id="id">
  document.addEventListener("click", function (e) {
    var opener = e.target.closest("[data-modal]");
    if (opener) {
      e.preventDefault();
      var m = document.getElementById(opener.dataset.modal);
      if (m) {
        m.classList.add("open");
        // pass data-* values into the modal's form fields: data-set-amount="1200"
        Object.keys(opener.dataset).forEach(function (k) {
          if (k.indexOf("set") === 0 && k.length > 3) {
            var name = k.slice(3).toLowerCase();
            var f = m.querySelector('[name="' + name + '"]');
            if (f) f.value = opener.dataset[k];
          }
        });
        if (opener.dataset.action) { var form = m.querySelector("form"); if (form) form.action = opener.dataset.action; }
        var first = m.querySelector("input:not([type=hidden]),select");
        if (first) setTimeout(function () { first.focus(); }, 50);
      }
    }
    if (e.target.classList.contains("modal") || e.target.closest("[data-close]")) {
      var md = e.target.closest(".modal");
      if (md) md.classList.remove("open");
    }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") document.querySelectorAll(".modal.open").forEach(function (m) { m.classList.remove("open"); });
  });

  // ---------- confirm on dangerous forms: <form data-confirm="Sure?">
  document.addEventListener("submit", function (e) {
    var msg = e.target.dataset.confirm;
    if (msg && !window.confirm(msg)) e.preventDefault();
  });

  // ---------- member autocomplete: <div class="ac" data-ac="url" data-go="member|pick">
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  window.escapeHtml = esc;
  window.avatarHtml = function (m, cls) {
    return '<div class="avatar ' + (cls || "") + '">' + (m.photo ? '<img src="' + esc(m.photo) + '" alt="">' : esc(m.initials)) + "</div>";
  };
  var BADGE = { active: "ok", expiring: "warn", expired: "bad", frozen: "info", upcoming: "info", none: "muted" };
  window.badgeHtml = function (st, label) { return '<span class="badge badge-' + (BADGE[st] || "muted") + '">' + esc(label) + "</span>"; };

  document.querySelectorAll(".ac").forEach(function (box) {
    var input = box.querySelector("input"), list = box.querySelector(".ac-list"), timer, items = [], hl = -1;
    function render() {
      if (!items.length) { list.innerHTML = '<div class="empty small">' + esc(GYM.t.noResult) + "</div>"; list.classList.remove("hidden"); return; }
      list.innerHTML = items.map(function (m, i) {
        return '<a href="/members/' + m.id + '/" data-i="' + i + '" class="' + (i === hl ? "hl" : "") + '">' + avatarHtml(m) +
          '<div style="flex:1;min-width:0"><b>' + esc(m.name) + '</b><div class="small muted">' + esc(m.code) + " · " + esc(m.phone || "") + "</div></div>" +
          badgeHtml(m.status, m.status_label) + "</a>";
      }).join("");
      list.classList.remove("hidden");
    }
    function pick(i) {
      var m = items[i]; if (!m) return;
      if (box.dataset.go === "member") { location.href = "/members/" + m.id + "/"; return; }
      list.classList.add("hidden");
      box.dispatchEvent(new CustomEvent("pick", { detail: m }));
    }
    input.addEventListener("input", function () {
      clearTimeout(timer);
      var q = input.value.trim();
      if (q.length < 1) { list.classList.add("hidden"); return; }
      timer = setTimeout(function () {
        fetch(box.dataset.ac + "?q=" + encodeURIComponent(q)).then(function (r) { return r.json(); }).then(function (d) { items = d.results; hl = 0; render(); });
      }, 180);
    });
    input.addEventListener("keydown", function (e) {
      if (list.classList.contains("hidden")) return;
      if (e.key === "ArrowDown") { hl = Math.min(hl + 1, items.length - 1); render(); e.preventDefault(); }
      else if (e.key === "ArrowUp") { hl = Math.max(hl - 1, 0); render(); e.preventDefault(); }
      else if (e.key === "Enter" && box.dataset.go !== "none") { if (items[hl]) { e.preventDefault(); pick(hl); } }
    });
    list.addEventListener("click", function (e) {
      var a = e.target.closest("a[data-i]"); if (!a) return;
      if (box.dataset.go !== "member") { e.preventDefault(); pick(+a.dataset.i); }
    });
    document.addEventListener("click", function (e) { if (!box.contains(e.target)) list.classList.add("hidden"); });
  });

  // ---------- "Install app" button (desktop icon / phone home screen) when opened from a link
  var deferredInstall = null, ib = document.getElementById("installBtn");
  window.addEventListener("beforeinstallprompt", function (e) { e.preventDefault(); deferredInstall = e; if (ib) ib.classList.remove("hidden"); });
  if (ib) ib.addEventListener("click", function () { if (!deferredInstall) return; deferredInstall.prompt(); deferredInstall.userChoice.then(function () { deferredInstall = null; ib.classList.add("hidden"); }); });
  window.addEventListener("appinstalled", function () { if (ib) ib.classList.add("hidden"); });

  // ---------- chart defaults
  window.chartColors = function () {
    var dark = document.documentElement.dataset.theme === "dark";
    return { grid: dark ? "#22322d" : "#eef2f6", text: dark ? "#8fa39d" : "#64748b", primary: "#0e9f6e", red: "#ef4444",
      palette: ["#0e9f6e", "#2563eb", "#f59e0b", "#8b5cf6", "#ef4444", "#14b8a6", "#ec4899", "#64748b"] };
  };
  window.setupChart = function () {
    if (!window.Chart) return;
    var c = chartColors();
    Chart.defaults.color = c.text;
    Chart.defaults.borderColor = c.grid;
    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    Chart.defaults.plugins.legend.labels.boxWidth = 12;
    Chart.defaults.maintainAspectRatio = false;
  };
})();
