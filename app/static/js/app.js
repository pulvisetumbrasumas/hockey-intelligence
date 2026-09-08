/* ============================================================
   HOCKEY INTELLIGENCE — CORE APP
   Namespace: window.HI
   Router (hash), API layer, global search, account + favorites
   (local-first shell), notifications, modals, toasts, helpers.
   ============================================================ */
(function () {
  "use strict";

  const $ = (sel, el) => (el || document).querySelector(sel);
  const $$ = (sel, el) => Array.from((el || document).querySelectorAll(sel));

  function escape(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  /* ---------- Local store ---------- */
  const store = {
    get(k, fb) {
      try {
        const v = localStorage.getItem("hi." + k);
        return v ? JSON.parse(v) : fb;
      } catch (_) {
        return fb;
      }
    },
    set(k, v) {
      try { localStorage.setItem("hi." + k, JSON.stringify(v)); } catch (_) {}
    },
  };

  const account = {
    get() { return store.get("account", null); },
    save(p) { store.set("account", p); },
    clear() { store.set("account", null); },
  };

  const favorites = {
    list() { return store.get("favorites", []); },
    has(type, id) { return favorites.list().some((f) => f.type === type && f.id === id); },
    toggle(item) {
      let list = favorites.list();
      if (favorites.has(item.type, item.id)) {
        list = list.filter((f) => !(f.type === item.type && f.id === item.id));
      } else {
        list.push(item);
      }
      store.set("favorites", list);
      favorites.updateBadge();
      return favorites.has(item.type, item.id);
    },
    updateBadge() {
      const el = $("#fav-count");
      if (!el) return;
      const n = favorites.list().length;
      el.textContent = n;
      el.classList.toggle("hidden", n === 0);
    },
  };

  /* ---------- API ---------- */
  async function api(path) {
    const resp = await fetch(path, {
      headers: { "Accept": "application/json" },
    });
    if (!resp.ok) {
      let detail = resp.statusText;
      try {
        const body = await resp.json();
        detail = body.detail || detail;
      } catch (_) {}
      throw new Error(detail);
    }
    return resp.json();
  }

  async function apiPost(path, body) {
    const resp = await fetch(path, {
      method: "POST",
      headers: { "Accept": "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!resp.ok) {
      let detail = resp.statusText;
      try {
        const body = await resp.json();
        detail = body.detail || detail;
      } catch (_) {}
      throw new Error(detail);
    }
    return resp.json();
  }

  /* ---------- Toast + modal ---------- */
  function toast(msg, ms) {
    const wrap = $("#toasts");
    const t = document.createElement("div");
    t.className = "toast";
    t.textContent = msg;
    wrap.appendChild(t);
    setTimeout(() => {
      t.style.opacity = "0";
      t.style.transition = "opacity .4s";
      setTimeout(() => t.remove(), 400);
    }, ms || 2600);
  }

  function modal({ title, sub, body, actions }) {
    const back = $("#modal-back");
    const box = $("#modal-box");
    box.innerHTML =
      '<div class="row" style="justify-content:space-between;align-items:flex-start;gap:14px;">' +
      '<div><h2>' + escape(title || "") + "</h2>" +
      (sub ? '<div class="sub">' + escape(sub) + "</div>" : "") + "</div>" +
      '<button class="icon-btn" data-close aria-label="Close">✕</button></div>' +
      '<div class="modal-body">' + body + "</div>" +
      (actions ? '<div class="row" style="margin-top:18px;flex-wrap:wrap;justify-content:flex-end;">' + actions + "</div>" : "");
    back.classList.remove("hidden");
    back.focus();
    const onKey = (e) => { if (e.key === "Escape") closeModal(); };
    document.addEventListener("keydown", onKey, { once: true });
    back.addEventListener(
      "click",
      (e) => { if (e.target === back || e.target.closest("[data-close]")) closeModal(); },
      { once: true }
    );
    function closeModal() {
      back.classList.add("hidden");
      document.removeEventListener("keydown", onKey);
    }
  }

  /* ---------- Countdown ---------- */
  function startCountdown(targetEpochMs, cb) {
    if (!targetEpochMs) return;
    function tick() {
      let diff = targetEpochMs - Date.now();
      if (diff < 0) diff = 0;
      const d = Math.floor(diff / 86400000);
      const h = Math.floor((diff % 86400000) / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      cb({ d, h, m, s, done: diff === 0 });
    }
    tick();
    return setInterval(tick, 1000);
  }

  function countdownHtml(field) {
    return (
      '<div class="countdown" data-countdown="' + field + '">' +
      '<div class="cd-cell primary"><div class="v" data-cd="d">—</div><div class="l">Days</div></div>' +
      '<div class="cd-cell"><div class="v" data-cd="h">—</div><div class="l">Hours</div></div>' +
      '<div class="cd-cell"><div class="v" data-cd="m">—</div><div class="l">Minutes</div></div>' +
      '<div class="cd-cell"><div class="v" data-cd="s">—</div><div class="l">Seconds</div></div>' +
      "</div>"
    );
  }

  function bindCountdown(root, targetEpochMs) {
    const el = root.querySelector("[data-countdown]");
    if (!el || !targetEpochMs) return;
    startCountdown(targetEpochMs, ({ d, h, m, s }) => {
      el.querySelector("[data-cd=d]").textContent = String(d).padStart(2, "0");
      el.querySelector("[data-cd=h]").textContent = String(h).padStart(2, "0");
      el.querySelector("[data-cd=m]").textContent = String(m).padStart(2, "0");
      el.querySelector("[data-cd=s]").textContent = String(s).padStart(2, "0");
    });
  }

  function epochMs(dateStr) {
    if (!dateStr) return 0;
    const t = Date.parse(dateStr.includes("T") ? dateStr : dateStr + "T00:00:00Z");
    return isNaN(t) ? 0 : t;
  }

  /* ---------- Helpers ---------- */
  function fmtNum(n) {
    return (n == null || isNaN(n)) ? "—" : Number(n).toLocaleString("en-US");
  }

  function initials(name) {
    return String(name || "?")
      .split(/\s+/)
      .slice(0, 2)
      .map((w) => (w[0] || "").toUpperCase())
      .join("");
  }

  function favBtn(item) {
    const active = favorites.has(item.type, item.id);
    return (
      '<button class="btn sm ghost fav-toggle" data-type="' + escape(item.type) +
      '" data-id="' + item.id + '" data-name="' + escape(item.name || "") +
      '" data-sub="' + escape(item.sub || "") + '" title="Save to favorites">' +
      (active ? "★ Saved" : "☆ Follow") + "</button>"
    );
  }

  function bindFavButtons(root) {
    $$(".fav-toggle", root).forEach((b) => {
      b.addEventListener("click", (e) => {
        e.stopPropagation();
        const item = {
          type: b.dataset.type,
          id: b.dataset.id,
          name: b.dataset.name,
          sub: b.dataset.sub,
        };
        const added = favorites.toggle(item);
        b.textContent = added ? "★ Saved" : "☆ Follow";
        toast(added ? "Saved to My Favorites" : "Removed from My Favorites");
      });
    });
  }

  /* ---------- Render helpers ---------- */
  function mount(id, html, after) {
    const el = document.getElementById(id);
    el.innerHTML = html;
    if (after) after(el);
    bindFavButtons(el);
    el.scrollTop = 0;
    return el;
  }

  function navTo(hash) {
    if (location.hash === hash) { route(); }
    else { location.hash = hash; }
  }

  /* ---------- Router ---------- */
  const NAV = [
    ["home", "Home", "#/home"],
    ["live", "Live NHL", "#/live"],
    ["schedule", "Schedule & Scores", "#/schedule"],
    ["standings", "Standings", "#/standings"],
    ["players", "Players", "#/players"],
    ["teams", "Teams", "#/teams"],
    ["franchises", "Franchises", "#/franchises"],
    ["history", "History", "#/history"],
    ["compare", "Compare", "#/compare"],
    ["fantasy", "Fantasy", "#/fantasy"],
    ["ai", "AI Analyst", "#/ai"],
    ["news", "News", "#/news"],
    ["events", "Events", "#/events"],
    ["favorites", "My Favorites", "#/favorites"],
    ["settings", "Settings", "#/settings"],
  ];

  function renderNav() {
    const track = $("#nav-track");
    const hash = location.hash.split("?")[0].replace(/^[#/]+/, "");
    track.innerHTML = NAV.map(
      ([key, label, h]) =>
        '<a class="nav-pill' + (hash === key ? " active" : "") + '" href="' + h +
        '" data-navkey="' + key + '">' + escape(label) + "</a>"
    ).join("");
  }

  const ROUTES = {
    home: HI_Home,
    live: HI_Live,
    schedule: HI_Schedule,
    standings: HI_Standings,
    players: HI_Players,
    teams: HI_Teams,
    franchises: HI_Franchises,
    history: HI_History,
    compare: HI_Compare,
    fantasy: HI_Fantasy,
    ai: HI_AI,
    news: HI_News,
    events: HI_Events,
    favorites: HI_Favorites,
    settings: HI_Settings,
  };

  function route() {
    renderNav();
    const clean = location.hash.replace(/^#\/?/, "").split("?")[0];
    const parts = clean.split("/").filter(Boolean);
    const key = parts[0] || "home";
    const handler = ROUTES[key] || (() => "<div class='error-block'>Unknown destination.</div>");
    const view = $("#view");
    view.innerHTML = '<div class="loading-block"><div class="spinner"></div>Loading…</div>';
    Promise.resolve()
      .then(() => handler({ parts }))
      .then((res) => {
        const html = typeof res === "string" ? res : res.html;
        view.innerHTML = html || "";
        if (window.HI && window.HI.bindFavButtons) {
          window.HI.bindFavButtons(view);
        }
        if (res && typeof res.bind === "function") {
          try { res.bind(view); } catch (err) { console.error(err); }
        }
        document.title =
          (key.charAt(0).toUpperCase() + key.slice(1)) + " · Hockey Intelligence";
        view.focus({ preventScroll: true });
      })
      .catch((err) => {
        console.error(err);
        view.innerHTML =
          "<div class='error-block'>" + HI.escape((err && err.message) || String(err)) + "</div>";
      });
  }

  /* ---------- Global search ---------- */
  function bindSearch() {
    const input = $("#search-input");
    const drop = $("#search-drop");
    let timer = null;
    let items = [];
    let active = -1;

    const close = () => { drop.classList.add("hidden"); active = -1; };
    const open = () => { drop.classList.remove("hidden"); };

    input.addEventListener("input", () => {
      clearTimeout(timer);
      const q = input.value.trim();
      if (q.length < 2) { close(); return; }
      timer = setTimeout(async () => {
        try {
          const data = await api("/api/search?q=" + encodeURIComponent(q) + "&limit=6");
          items = [];
          let html = "";
          if (data.players && data.players.length) {
            html += '<div class="search-group"><h6>Players</h6>';
            data.players.forEach((p) => {
              items.push({ kind: "player", hash: "#/players/" + p.player_id, label: p.full_name });
              const img = p.headshot || '<span class="mono">' + escape(initials(p.full_name)) + "</span>";
              html += '<div class="search-item" data-i="' + (items.length - 1) + '">' +
                '<img alt="" loading="lazy" src="' + escape(p.headshot || "") + '" onerror="this.style.display=\'none\'">' +
                '<span class="grow"><span class="lead">' + escape(p.full_name) + "</span>" +
                ' <span class="sub">' + escape(p.position || "") + (p.team_abbreviation ? " · " + escape(p.team_abbreviation) : "") + "</span></span></div>";
            });
            html += "</div>";
          }
          if (data.teams && data.teams.length) {
            html += '<div class="search-group"><h6>Teams</h6>';
            data.teams.forEach((t) => {
              items.push({ kind: "team", hash: "#/teams/" + t.team_id, label: t.full_name });
              html += '<div class="search-item" data-i="' + (items.length - 1) + '">' +
                '<img alt="" loading="lazy" src="' + escape(t.logo || "") + '" onerror="this.style.display=\'none\'">' +
                '<span class="grow"><span class="lead">' + escape(t.full_name) + "</span>" +
                ' <span class="sub">' + escape(t.abbreviation || "") + "</span></span></div>";
            });
            html += "</div>";
          }
          if (data.franchises && data.franchises.length) {
            html += '<div class="search-group"><h6>Franchises</h6>';
            data.franchises.forEach((f) => {
              items.push({ kind: "franchise", hash: "#/franchises/" + f.franchise_id, label: f.full_name });
              html += '<div class="search-item" data-i="' + (items.length - 1) + '">' +
                '<span class="grow"><span class="lead">' + escape(f.full_name) + "</span>" +
                ' <span class="sub">Est. ' + escape(f.established_year || "?") + "</span></span></div>";
            });
            html += "</div>";
          }
          if (!html) {
            html = '<div class="search-group"><div class="search-item"><span class="sub">No results</span></div></div>';
          }
          drop.innerHTML = html;
          active = -1;
          open();
        } catch (_) { close(); }
      }, 220);
    });

    drop.addEventListener("mousedown", (e) => {
      const item = e.target.closest(".search-item");
      if (!item) return;
      const entry = items[Number(item.dataset.i)];
      if (!entry) return;
      input.value = "";
      close();
      navTo(entry.hash);
    });

    input.addEventListener("keydown", (e) => {
      if (e.key === "Escape") { close(); input.blur(); }
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        if (!items.length) return;
        active = e.key === "ArrowDown" ? (active + 1) % items.length : (active - 1 + items.length) % items.length;
        $$(".search-item", drop).forEach((el, i) => el.classList.toggle("active", i === active));
        const el = $$(".search-item", drop)[active];
        if (el) el.scrollIntoView({ block: "nearest" });
      }
      if (e.key === "Enter" && active >= 0 && items[active]) {
        input.value = "";
        close();
        navTo(items[active].hash);
      }
    });

    document.addEventListener("click", (e) => {
      if (!e.target.closest(".top-search")) close();
    });

    /* global / focuses search */
    document.addEventListener("keydown", (e) => {
      if (e.key === "/" && !/INPUT|TEXTAREA/.test(document.activeElement.tagName)) {
        e.preventDefault();
        input.focus();
        input.select();
      }
    });
  }

  /* ---------- Account / profile ---------- */
  function updateAccountUI() {
    const a = account.get();
    const avatar = $("#account-avatar");
    const full = a && a.name ? initials(a.name) : "?";
    avatar.textContent = full;
    if (a) avatar.style.borderColor = "#35d7ff";
  }

  function bindAccountModal() {
    $("#btn-account").addEventListener("click", () => {
      const a = account.get();
      if (a) {
        modal({
          title: a.name,
          sub: a.email || "Local profile",
          body:
            '<div class="factgrid"><div class="fact"><div class="k">Account type</div><div class="v">Local profile</div></div>' +
            '<div class="fact"><div class="k">Server accounts</div><div class="v">Later phase</div></div></div>' +
            '<p class="sub" style="margin-top:14px;">This phase keeps your profile, favorites and settings on this browser only. Full accounts (login, preferences, sync) land in a later vertical slice.</p>',
          actions:
            '<a class="btn ghost" href="#/favorites" data-close>My Favorites</a>' +
            '<button class="btn red" id="signout">Sign out</button>',
        });
        setTimeout(() => {
          const so = $("#signout");
          if (so) so.addEventListener("click", () => {
            account.clear();
            updateAccountUI();
            closeModal();
            toast("Signed out.");
          });
        }, 0);
      } else {
        modal({
          title: "Welcome",
          sub: "Create a local profile to personalize the platform.",
          body:
            '<div class="field-row"><input class="field" id="reg-name" placeholder="Display name" autocomplete="name" /></div>' +
            '<div class="field-row"><input class="field" id="reg-email" type="email" placeholder="Email (optional)" autocomplete="email" /></div>' +
            '<p class="sub" style="margin:4px 0 0;">Stored in this browser only — server accounts arrive in a later slice.</p>',
          actions:
            '<button class="btn red" id="reg-skip">Explore as guest</button>' +
            '<button class="btn accent" id="reg-save">Create profile</button>',
        });
        setTimeout(() => {
          $("#reg-save").addEventListener("click", () => {
            const name = $("#reg-name").value.trim() || "Guest Fan";
            const email = $("#reg-email").value.trim();
            account.save({ name, email });
            updateAccountUI();
            closeModal();
            toast("Profile created — welcome, " + name + "!");
          });
          $("#reg-skip").addEventListener("click", () => { closeModal(); });
        }, 0);
      }
    });
  }

  function closeModal() {
    $("#modal-back").classList.add("hidden");
  }

  /* ---------- Notifications ---------- */
  function bindNotifications() {
    $("#btn-bell").addEventListener("click", () => {
      const a = account.get();
      modal({
        title: "Notifications",
        sub: "Local, data-driven alerts",
        body:
          '<div class="empty"><div class="glyph">🔔</div><h4>Quiet for now</h4>' +
          "<p>Countdown and follow alerts will surface here once the events and favorite-tracking slices land. The bell indicator shown is a visual placeholder.</p></div>" +
          '<p class="sub" style="font-size:12px;">' + escape(a ? "Profile: " + a.name + (a.email ? " · " + a.email : "") : "Guest") + "</p>",
        actions: '<button class="btn accent" data-close>Done</button>',
      });
    });
  }

  /* ---------- Footer status ---------- */
  async function bootStatus() {
    try {
      const h = await api("/health");
      const el = $("#footer-status");
      el.textContent = "live · engine " + h.model_configured;
    } catch (_) {
      $("#footer-status").textContent = "offline";
    }
  }

  /* ---------- Init ---------- */
  function init() {
    renderNav();
    bindSearch();
    bindAccountModal();
    bindNotifications();
    updateAccountUI();
    favorites.updateBadge();
    bootStatus();

    $$(".topbar [data-nav]").forEach((b) =>
      b.addEventListener("click", () => navTo(b.dataset.nav))
    );
    document.getElementById("btn-star").addEventListener("click", () => navTo("#/favorites"));

    window.addEventListener("hashchange", route);
    if (!location.hash) location.hash = "#/home";
    else route();
  }

  window.HI = {
    $, $$, escape, api, apiPost, toast, modal, closeModal,
    mount, navTo, startCountdown, countdownHtml, bindCountdown, epochMs,
    fmtNum, initials, favBtn, bindFavButtons,
    favorites, account, store,
    NAV,
    init,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();