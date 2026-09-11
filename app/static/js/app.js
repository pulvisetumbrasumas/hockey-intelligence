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
    get() { return store.get("session", null); },
    token() { const s = store.get("session", null); return s && s.token ? s.token : null; },
    save(p) { store.set("session", p); },
    clear() { store.set("session", null); },
  };

  let cachedServerFavorites = [];
  const favorites = {
    list() {
      if (account.token()) return cachedServerFavorites;
      return store.get("favorites", []);
    },
    has(type, id) {
      return favorites.list().some(
        (f) => (f.item_type || f.type) === type && String(f.item_key || f.id) === String(id)
      );
    },
    toggle(item) {
      let list = account.token() ? cachedServerFavorites : store.get("favorites", []);
      const exists = list.some(
        (f) => (f.item_type || f.type) === item.type && String(f.item_key || f.id) === String(item.id)
      );
      if (exists) {
        list = list.filter(
          (f) => !((f.item_type || f.type) === item.type && String(f.item_key || f.id) === String(item.id))
        );
      } else {
        list.push({ item_type: item.type, item_key: item.id, label: item.name });
      }
      if (account.token()) {
        cachedServerFavorites = list;
        if (exists) apiDelete("/api/account/favorites/" + item.type + "/" + item.id).catch(() => {});
        else apiPost("/api/account/favorites", { item_type: item.type, item_key: item.id, label: item.name }).catch(() => {});
      } else {
        store.set("favorites", list);
      }
      favorites.updateBadge();
      return !exists;
    },
    remove(item) {
      const type = item.type || item.item_type;
      const id = item.id != null ? item.id : item.item_key;
      if (account.token()) {
        cachedServerFavorites = cachedServerFavorites.filter(
          (f) => !((f.item_type || f.type) === type && String(f.item_key || f.id) === String(id))
        );
        apiDelete("/api/account/favorites/" + type + "/" + id).catch(() => {});
      } else {
        let list = store.get("favorites", []).filter(
          (f) => !((f.type || f.item_type) === type && String(f.id != null ? f.id : f.item_key) === String(id))
        );
        store.set("favorites", list);
      }
      favorites.updateBadge();
    },
    async sync() {
      if (!account.token()) return;
      try {
        cachedServerFavorites = await api("/api/account/favorites");
        cachedServerFavorites = cachedServerFavorites.favorites || [];
      } catch (_) {}
      favorites.updateBadge();
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
  function authHeaders(extra) {
    const h = { "Accept": "application/json", ...(extra || {}) };
    const t = account.token();
    if (t) h["Authorization"] = "Bearer " + t;
    return h;
  }

  async function api(path) {
    const resp = await fetch(path, { headers: authHeaders() });
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
      headers: authHeaders({ "Content-Type": "application/json" }),
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

  async function apiDelete(path) {
    const resp = await fetch(path, { method: "DELETE", headers: authHeaders() });
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
    ["playoffs", "Playoffs", "#/playoffs"],
    ["players", "Players", "#/players"],
    ["teams", "Teams", "#/teams"],
    ["franchises", "Franchises", "#/franchises"],
    ["history", "History", "#/history"],
    ["champions", "Champions", "#/champions"],
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
    home: "HI_Home",
    live: "HI_Live",
    schedule: "HI_Schedule",
    standings: "HI_Standings",
    playoffs: "HI_Playoffs",
    players: "HI_Players",
    teams: "HI_Teams",
    franchises: "HI_Franchises",
    history: "HI_History",
    champions: "HI_Champions",
    compare: "HI_Compare",
    fantasy: "HI_Fantasy",
    ai: "HI_AI",
    news: "HI_News",
    events: "HI_Events",
    favorites: "HI_Favorites",
    settings: "HI_Settings",
  };

  function route() {
    renderNav();
    const hashClean = location.hash.replace(/^#\/?/, "");
    const [pathBits, rawQuery] = hashClean.split("?");
    const parts = pathBits.split("/").filter(Boolean);
    const query = {};
    (rawQuery || "").split("&").forEach((kv) => {
      if (!kv) return;
      const idx = kv.indexOf("=");
      const k = idx >= 0 ? kv.slice(0, idx) : kv;
      const v = idx >= 0 ? kv.slice(idx + 1) : "";
      if (k) query[decodeURIComponent(k)] = decodeURIComponent(v);
    });
    const key = parts[0] || "home";
    const handler = window[ROUTES[key]] || (() => "<div class='error-block'>Unknown destination.</div>");
    const view = $("#view");
    view.innerHTML = '<div class="loading-block"><div class="spinner"></div>Loading…</div>';
    Promise.resolve()
      .then(() => handler({ parts, query }))
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
  function currentUser() {
    const s = account.get();
    return s && s.user ? s.user : null;
  }

  function updateAccountUI() {
    const u = currentUser();
    const avatar = $("#account-avatar");
    const full = u ? initials(u.display_name || u.username) : "?";
    avatar.textContent = full;
    if (u) avatar.style.borderColor = "#35d7ff";
    else avatar.style.borderColor = "";
  }

  function bindAccountModal() {
    $("#btn-account").addEventListener("click", () => {
      const u = currentUser();
      if (u) {
        modal({
          title: u.display_name || u.username,
          sub: "@" + u.username + (u.created_at ? " · member since " + String(u.created_at).slice(0, 10) : ""),
          body:
            '<div class="factgrid"><div class="fact"><div class="k">Account type</div><div class="v">Server account</div></div>' +
            '<div class="fact"><div class="k">Signed in</div><div class="v">Yes</div></div></div>' +
            '<p class="sub" style="margin-top:14px;">Favorites and notification preferences sync to your account and follow you between browsers.</p>',
          actions:
            '<a class="btn ghost" href="#/favorites" data-close>My Favorites</a>' +
            '<button class="btn accent" id="signout">Sign out</button>' +
            '<button class="btn red" id="delete-account">Delete account</button>',
        });
        setTimeout(() => {
          const so = $("#signout");
          if (so) so.addEventListener("click", () => {
            const t = account.token();
            account.clear();
            if (t) apiPost("/api/account/logout", {}).catch(() => {});
            cachedServerFavorites = [];
            favorites.updateBadge();
            updateAccountUI();
            closeModal();
            toast("Signed out. Favorites returned to this browser.");
          });
          const del = $("#delete-account");
          if (del) del.addEventListener("click", async () => {
            try {
              await apiDelete("/api/account/me");
            } catch (_) {}
            account.clear();
            cachedServerFavorites = [];
            favorites.updateBadge();
            updateAccountUI();
            closeModal();
            toast("Account deleted.");
          });
        }, 0);
      } else {
        const errEl = () =>
          '<p class="sub" style="color:var(--red-soft);margin:10px 0 0;display:none;" id="account-err"></p>';
        modal({
          title: "Welcome",
          sub: "Sign in to sync favorites and notifications across devices.",
          body:
            '<div class="field-row"><input class="field" id="acct-username" placeholder="Username" autocomplete="username" /></div>' +
            '<div class="field-row"><input class="field" id="acct-display" placeholder="Display name (new accounts only)" autocomplete="nickname" /></div>' +
            '<div class="field-row"><input class="field" id="acct-password" type="password" placeholder="Password (6+ chars)" autocomplete="current-password" /></div>' + errEl(),
          actions:
            '<button class="btn ghost" id="acct-login">Sign in</button>' +
            '<button class="btn accent" id="acct-register">Create account</button>',
        });
        setTimeout(() => {
          const showErr = (m) => {
            const el = $("#account-err");
            if (el) { el.textContent = m; el.style.display = "block"; }
          };
          const finish = (data) => {
            account.save({ token: data.token, user: data.user });
            favorites.sync().then(() => {
              updateAccountUI();
              closeModal();
              toast("Welcome, " + (data.user.display_name || data.user.username) + "!");
            });
          };
          const submit = async (mode) => {
            const username = $("#acct-username").value.trim();
            const password = $("#acct-password").value;
            if (!username || !password) { showErr("Username and password are required."); return; }
            try {
              const data = mode === "register"
                ? await apiPost("/api/account/register", {
                    username, password,
                    display_name: $("#acct-display").value.trim() || username,
                  })
                : await apiPost("/api/account/login", { username, password });
              finish(data);
            } catch (err) {
              showErr(err && err.message ? err.message : "Sign-in failed.");
            }
          };
          $("#acct-login").addEventListener("click", () => submit("login"));
          $("#acct-register").addEventListener("click", () => submit("register"));
        }, 0);
      }
    });
  }

  function closeModal() {
    $("#modal-back").classList.add("hidden");
  }

  /* ---------- Notifications ---------- */
  function bindNotifications() {
    $("#btn-bell").addEventListener("click", async () => {
      const u = currentUser();
      if (!u) {
        modal({
          title: "Notifications",
          sub: "Signed in required",
          body:
            '<div class="empty"><h4>Notifications live on your account</h4>' +
            "<p>Create or sign in to your account, then pick the league events you care about in Settings — we'll remind you as they approach.</p></div>",
          actions:
            '<button class="btn accent" data-close id="notif-signin">Sign in</button>',
        });
        setTimeout(() => {
          const go = $("#notif-signin");
          if (go) go.addEventListener("click", () => { closeModal(); $("#btn-account").click(); });
        }, 0);
        return;
      }
      let items;
      try {
        const data = await api("/api/account/notifications");
        items = data.notifications || [];
      } catch (_) { items = []; }
      modal({
        title: "Notifications",
        sub: "@" + u.username + " · upcoming within your lead windows",
        body:
          items.length
            ? items.map((n) =>
                '<a class="row" style="justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--line-soft);text-decoration:none;">' +
                '<span class="grow"><span style="font-weight:600;">' + escape(n.title) + '</span>' +
                '<span class="dim" style="display:block;font-size:12px;">' + escape(n.date || "") +
                " · " + escape(n.source || "") + "</span></span>" +
                '<span class="pill-tag cyan">in ' + escape(String(n.days_until)) + "d</span></a>"
              ).join("")
            : '<div class="empty"><h4>All quiet</h4><p>Set event windows in Settings to get head-ups here as league events approach.</p></div>',
        actions:
          '<a class="btn ghost" href="#/settings?section=notification-prefs" data-close>Manage preferences</a>',
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
    favorites.sync();
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
    $, $$, escape, api, apiPost, apiDelete, authHeaders, toast, modal, closeModal,
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