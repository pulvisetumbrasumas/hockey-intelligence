/* ============================================================
   SCHEDULE · EVENTS · HISTORY · FANTASY · NEWS · FAVORITES · SETTINGS
   ============================================================ */
(function () {
  "use strict";
  const HI_ = window.HI.escape;
  const L = window.HI.fmtNum;

  function LOGO(u) { return u || "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3C/svg%3E"; }

  /* ---------------- Schedule ---------------- */
  async function schedule(ctx) {
    try {
      const today = new Date();
      const iso = today.toISOString().slice(0, 10);
      const data = await window.HI.api("/api/schedule?date=today");

      const gameRow = (g) => {
        const live = g.state === "LIVE" || g.state === "CRIT";
        const final = g.state === "FINAL" || g.state === "OFF";
        const awayWin = final && g.away.score > g.home.score;
        const homeWin = final && g.home.score > g.away.score;
        const row = (team, win) =>
          '<div class="teamline' + (final && win ? " winner" : "") + '"><span class="logo"><img alt="" loading="lazy" src="' + LOGO(team.logo) + '"></span>' +
          '<span class="tname">' + HI_(team.name) + "</span>" +
          '<span class="score">' + (final || live ? L(team.score) : "") + "</span></div>";
        return '<div class="game-card">' +
          '<div class="gstate"><span>' + HI_(g.game_type || "") + "</span><span>" +
          (live ? '<span class="live"><span class="live-dot"></span>' + (g.clock || "P" + (g.period || "")) + "</span>" : final ? "Final" : HI_(g.eastern_time || "TBA")) +
          "</span></div>" + row(g.away, awayWin) + row(g.home, homeWin) + "</div>";
      };

      const html =
        '<h1 class="page-title">Schedule & Scores</h1>' +
        '<p class="page-sub">Live slate pulled from the NHL schedule endpoint. During the offseason the board goes quiet and the season countdown takes over.</p>' +
        '<div class="row wrap" style="margin-bottom:18px;gap:10px;">' +
        '<button class="btn sm" id="sched-prev">← Previous day</button>' +
        '<button class="btn sm accent" id="sched-today">Today</button>' +
        '<button class="btn sm" id="sched-next">Next date →</button>' +
        '<span class="pill-tag cyan" id="sched-date">' + HI_(data.date || iso) + "</span>" +
        "</div>" +
        '<div id="sched-games">' + (data.games && data.games.length
          ? '<div class="grid" style="grid-template-columns:repeat(auto-fill,minmax(300px,1fr));">' + data.games.map(gameRow).join("") + "</div>"
          : '<div class="empty"><div class="glyph">📅</div><h4>No games on this date</h4><p>Next league date: ' + HI_(data.next_start_date || "TBA") + ".</p></div>") +
        "</div>";

      return {
        html,
        async bind(view) {
          const show = async (dateKey) => {
            const box = view.querySelector("#sched-games");
            box.innerHTML = '<div class="loading-block"><div class="spinner"></div>;</div>';
            try {
              const d = await window.HI.api("/api/schedule?date=" + encodeURIComponent(dateKey));
              view.querySelector("#sched-date").textContent = d.date;
              box.innerHTML = d.games && d.games.length
                ? '<div class="grid" style="grid-template-columns:repeat(auto-fill,minmax(300px,1fr));">' + d.games.map(gameRow).join("") + "</div>"
                : '<div class="empty"><div class="glyph">📅</div><h4>No games on this date</h4><p>Next league date: ' + HI_(d.next_start_date || "TBA") + ".</p></div>";
            } catch (err) {
              box.innerHTML = "<div class='error-block'>" + HI_(err && err.message) + "</div>";
            }
          };
          view.querySelector("#sched-today").addEventListener("click", () => show("today"));
          view.querySelector("#sched-next").addEventListener("click", () => show("next"));
          view.querySelector("#sched-prev").addEventListener("click", () => {
            const d = new Date();
            d.setDate(d.getDate() - 1);
            show(d.toISOString().slice(0, 10));
          });
        },
      };
    } catch (err) {
      return "<div class='error-block'>" + HI_(err && err.message) + "</div>";
    }
  }

  /* ---------------- Events ---------------- */
  async function events(ctx) {
    try {
      const data = await window.HI.api("/api/events");
      const items = (data.events || []).filter((e) => !e.is_past);
      const past = (data.events || []).filter((e) => e.is_past);
      const html =
        '<h1 class="page-title">Events & Countdowns</h1>' +
        '<p class="page-sub">League-wide milestones, driven by the NHL schedule API plus the configured calendar. Nothing is hard-coded in the UI.</p>' +
        '<div class="card"><div class="timeline" style="margin-top:8px;">' +
        (items.length ? items.map(eventItem).join("") : '<div class="empty"><h4>No upcoming events</h4></div>') +
        "</div></div>" +
        (past.length
          ? '<div class="section"><div><span class="eyebrow amber">Reached</span><h2>Recent</h2></div>' +
            '<div class="card" style="margin-top:12px;"><div class="timeline">' + items_completed(past) + "</div></div></div>"
          : "");
      return {
        html,
        bind(view) {
          const cells = [];
          view.querySelectorAll("[data-countdown]").forEach((el) => {
            const target = window.HI.epochMs(el.getAttribute("data-countdown"));
            window.HI.startCountdown(target, ({ d, h, m, s }) => {
              el.querySelectorAll("[data-cd]").forEach((c) => {
                const v = c.getAttribute("data-cd");
                c.textContent = String(({ d, h, m, s })[v]).padStart(2, "0");
              });
            });
          });
        },
      };
    } catch (err) {
      return "<div class='error-block'>" + HI_(err && err.message) + "</div>";
    }
  }

  function eventItem(e) {
    return (
      '<div class="tl-item"><div class="tl-date">' + HI_(e.date || "TBA") + " · " + HI_(e.source) + "</div>" +
      "<h4>" + HI_(e.title) + "</h4>" +
      '<div style="margin-top:8px;">' + window.HI.countdownHtml(e.date) + "</div>" +
      "<p>" + HI_(e.is_past ? "Reached." : "Counting down.") + "</p></div>"
    );
  }

  function items_completed(events) {
    return events
      .map((e) =>
        '<div class="tl-item"><div class="tl-date">' + HI_(e.date || "TBA") + "</div>" +
        "<h4>" + HI_(e.title) + "</h4></div>"
      )
      .join("");
  }

  /* ---------------- History ---------------- */
  async function history(ctx) {
    try {
      const data = await window.HI.api("/api/seasons");
      const seasons = data.seasons || [];
      return {
        html:
          '<h1 class="page-title">History</h1>' +
          '<p class="page-sub">The database archives every NHL season we track. Coverage is being layered in — the ten most recent seasons carry full player and team statistics today.</p>' +
          '<div class="grid" style="grid-template-columns:repeat(auto-fill,minmax(280px,1fr));margin-bottom:22px;">' +
          seasons.slice(0, 10).map((s) =>
            '<a href="#/standings" class="card hover" style="text-decoration:none;">' +
            '<span class="eyebrow">Season</span>' +
            '<div style="font-size:26px;font-weight:800;margin:4px 0;">' + HI_(s.label) + "</div>" +
            '<div class="muted" style="font-size:12.5px;">' +
            (s.start_date ? "Start " + HI_(s.start_date) : "") +
            (s.regular_season_end ? " · End " + HI_(s.regular_season_end) : "") +
            "</div>" +
            '<div class="row wrap" style="margin-top:10px;"><span class="pill-tag">' + L(s.total_regular_season_games || "—") + " games</span>" +
            '<span class="pill-tag cyan">View standings →</span></div></a>'
          ).join("") +
          "</div>" +
          '<div class="card"><div class="head"><h3>The archive</h3><span class="pill-tag gold">' + seasons.length + " seasons</span></div>" +
          '<div class="grid" style="grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px;">' +
          seasons.slice(10).map((s) =>
            '<span class="pill-tag" style="justify-content:space-between;">' + HI_(s.label) + "</span>"
          ).join("") +
          "</div>" +
          '<p class="panel-tip" style="margin-top:12px;">Champions, playoffs, and franchise-by-season standings arrive with the deeper history slice.</p></div>',
      };
    } catch (err) {
      return "<div class='error-block'>" + HI_(err && err.message) + "</div>";
    }
  }

  /* ---------------- Fantasy (draft-room slice) ---------------- */
  const FANTASY_SLOTS = [
    ["C", 2, "Centers"],
    ["LW", 2, "Left wings"],
    ["RW", 2, "Right wings"],
    ["D", 4, "Defensemen"],
    ["G", 1, "Goaltenders"],
  ];
  const BENCH_SLOTS = 2;

  async function fantasy(ctx) {
    try {
      let root;
      let preset = "standard";
      let tab = "skater";
      const saved = window.HI.store.get("roster", null);
      const picks = saved && saved.picks && typeof saved.picks === "object" ? saved.picks : {};
      const fmtS = (n) => (n == null ? "—" : (Number.isInteger(n) ? L(n) : n.toFixed(2)));
      const defaultPools = await Promise.all([
        window.HI.api("/api/fantasy/pool?stat_type=skater&preset=standard&limit=200"),
        window.HI.api("/api/fantasy/pool?stat_type=goalie&preset=standard&limit=80"),
      ]);
      let pools = { skater: defaultPools[0], goalie: defaultPools[1] };
      const presets = defaultPools[0].presets;

      const fetchPool = async (p) => {
        const [s, g] = await Promise.all([
          window.HI.api("/api/fantasy/pool?stat_type=skater&preset=" + encodeURIComponent(p) + "&limit=200"),
          window.HI.api("/api/fantasy/pool?stat_type=goalie&preset=" + encodeURIComponent(p) + "&limit=80"),
        ]);
        pools = { skater: s, goalie: g };
      };

      const slotSpace = (pos) => {
        const def = FANTASY_SLOTS.find((f) => f[0] === pos);
        return def ? def[1] - (picks[pos] || []).length : 0;
      };

      const drawn = (pid) =>
        Object.keys(picks).some((k) =>
          (picks[k] || []).some((p) => String(p.player_id) === pid)
        );

      const draft = (row) => {
        const pid = String(row.player_id);
        if (drawn(pid)) {
          window.HI.toast(row.name + " is already on your roster.");
          return;
        }
        const pos = row.role === "goalie" ? "G" : (row.position || "D");
        const benchFree = BENCH_SLOTS - (picks.BN || []).length;
        if (slotSpace(pos) > 0) {
          picks[pos] = picks[pos] || [];
          picks[pos].push(row);
        } else if (benchFree > 0) {
          picks.BN = picks.BN || [];
          picks.BN.push(row);
        } else {
          window.HI.toast("Roster full for " + (row.position || "that") + " and bench.");
          return;
        }
        window.HI.store.set("roster", { preset, picks });
        renderRoster();
        renderPool();
      };

      const release = (pos, pid) => {
        picks[pos] = (picks[pos] || []).filter((p) => String(p.player_id) !== pid);
        window.HI.store.set("roster", { preset, picks });
        renderRoster();
        renderPool();
      };

      const releaseAll = () => {
        Object.keys(picks).forEach((k) => delete picks[k]);
        window.HI.store.set("roster", { preset, picks });
        renderRoster();
        renderPool();
      };

      const saveRoster = () => {
        window.HI.store.set("roster", { preset, picks });
        const n = Object.values(picks).reduce((a, l) => a + l.length, 0);
        window.HI.toast("Roster saved (" + n + " players).");
      };

      const rowCell = (r) => {
        const pos = r.role === "goalie" ? "G" : (r.position || "—");
        const picked = drawn(String(r.player_id));
        return (
          '<div class="row fantasy-row' + (picked ? " picked" : "") + '" data-pid="' + r.player_id + '"' +
          ' style="padding:7px 10px;cursor:pointer;border-bottom:1px solid var(--line-soft);gap:10px;">' +
          '<span class="rank" style="width:22px;height:22px;border-radius:6px;display:grid;place-items:center;font-size:10px;font-weight:700;background:rgba(255,255,255,.05);color:var(--text-3);">' + r.rank + "</span>" +
          '<span class="grow" style="min-width:0;"><span style="font-weight:600;">' + HI_(r.name) + '</span>' +
          '<span class="dim" style="font-size:11px;"> ' + HI_(r.team || "—") + " · " + HI_(pos) + "</span></span>" +
          '<span class="num" style="color:var(--cyan);font-weight:700;font-variant-numeric:tabular-nums;">' + fmtS(r.fp) + "</span>" +
          '<span class="dim" style="font-size:11px;width:52px;text-align:right;font-variant-numeric:tabular-nums;">' + (r.fp_per_game == null ? "—" : fmtS(r.fp_per_game) + "/g") + "</span>" +
          '<span class="pill-tag cyan" style="font-size:9px;flex:0 0 auto;">' + (picked ? "in" : "+") + "</span></div>"
        );
      };

      const renderPool = () => {
        const box = root.querySelector("#fp-pool");
        const role = pools[tab] || { results: [] };
        const list = (role.results || []).map((r) => rowCell({ ...r, role: tab })).join("");
        box.innerHTML =
          '<div class="row wrap" style="gap:8px;align-items:center;margin-bottom:10px;">' +
          '<span class="pill-tag gold">career-scoped</span>' +
          '<span class="dim" style="font-size:12px;">' + HI_(role.preset_label || preset) + " · " + HI_(role.preset_tagline || "") + "</span></div>" +
          '<div style="max-height:520px;overflow-y:auto;border:1px solid var(--line);border-radius:10px;">' +
          (list || '<div class="empty" style="padding:16px;"><h4>No data</h4></div>') +
          "</div>";
        root.querySelectorAll(".fantasy-row").forEach((row) =>
          row.addEventListener("click", () => {
            const r = (pools[tab].results || []).find(
              (x) => String(x.player_id) === String(row.dataset.pid)
            );
            if (r) draft({ ...r, role: tab });
          })
        );
      };

      const renderRoster = () => {
        const box = root.querySelector("#fp-roster");
        const slotBlock = (pos, count, label) => {
          const cells = Array.from({ length: count }, (_, i) => {
            const p = (picks[pos] || [])[i];
            return p
              ? '<div class="fchip filled" data-rel="release" data-pos="' + pos + '" data-pid="' + p.player_id + '" title="Click to release">' +
                '<b>' + HI_(p.name) + '</b><span>' + HI_(p.team || "—") + " · " + fmtS(p.fp) + " pts</span></div>"
              : '<div class="fchip empty"><span class="dim">' + HI_((pos === "G" ? "Goalie" : pos) + " slot " + (i + 1)) + "</span></div>";
          }).join("");
          return '<div class="fslot"><span class="dim" style="font-size:11px;">' + HI_(label) + "</span>" +
            '<div class="row wrap" style="gap:8px;">' + cells + "</div></div>";
        };
        const bench = Array.from({ length: BENCH_SLOTS }, (_, i) => {
          const p = (picks.BN || [])[i];
          return p
            ? '<div class="fchip bench filled" data-rel="release" data-pos="BN" data-pid="' + p.player_id + '" title="Click to release">' +
              '<b>' + HI_(p.name) + '</b><span>' + HI_(p.team || "—") + " · " + fmtS(p.fp) + ' pts</span></div>'
            : '<div class="fchip empty"><span class="dim">Bench</span></div>';
        }).join("");
        box.innerHTML =
          '<div style="display:grid;gap:12px;margin-bottom:14px;">' +
          FANTASY_SLOTS.map(([pos, count, label]) => slotBlock(pos, count, label)).join("") +
          '<div class="fslot"><span class="dim" style="font-size:11px;">Bench (' + BENCH_SLOTS + ')</span>' +
          '<div class="row wrap" style="gap:8px;">' + bench + "</div></div></div>" +
          '<div class="row wrap" style="gap:8px;">' +
          '<button class="btn accent" id="fp-save">Save roster</button>' +
          '<button class="btn ghost" id="fp-clear">Reset</button></div>';
        root.querySelectorAll("[data-rel=release]").forEach((chip) =>
          chip.addEventListener("click", () => release(chip.dataset.pos, chip.dataset.pid))
        );
        root.querySelector("#fp-save").addEventListener("click", saveRoster);
        root.querySelector("#fp-clear").addEventListener("click", releaseAll);
      };

      const renderPresets = () => {
        const wrap = root.querySelector("#fp-preset-wrap");
        wrap.innerHTML = (presets || [])
          .map(
            (p) =>
              '<button class="btn sm ' + (p.key === preset ? "accent" : "ghost") + '" data-fp-preset="' + p.key + '">' +
              HI_(p.key === "standard" ? "Standard" : p.key === "bangers" ? "Bangers" : "Pure points") + "</button>"
          ).join("");
        wrap.querySelectorAll("[data-fp-preset]").forEach((b) =>
          b.addEventListener("click", async () => {
            if (b.dataset.fpPreset === preset) return;
            preset = b.dataset.fpPreset;
            b.disabled = true;
            await fetchPool(preset);
            renderPresets();
            renderPool();
          })
        );
      };

      return {
        html:
          '<h1 class="page-title">Fantasy</h1>' +
          '<p class="page-sub"><b>Experimental, for fun</b> — an honest draft room powered by the same statistics engine as the rest of this platform. Draft real career leaders into a positions-based roster. Fantasy scoring is entertainment, never a claim about who is objectively best.</p>' +
          '<div class="row wrap" style="gap:8px;margin-bottom:14px;" id="fp-preset-wrap"></div>' +
          '<div class="row wrap" style="gap:16px;align-items:flex-start;">' +
          '<div class="card" style="flex:1.4;min-width:320px;">' +
          '<div class="head"><h3>Draft pool</h3>' +
          '<span class="row" style="gap:6px;"><button class="btn ghost sm" data-fp-tab="skater">Skaters</button>' +
          '<button class="btn ghost sm" data-fp-tab="goalie">Goalies</button></span></div>' +
          '<div id="fp-pool"></div></div>' +
          '<div class="card" style="flex:1;min-width:300px;">' +
          '<div class="head"><h3>Your roster</h3><span class="pill-tag gold">simulation</span></div>' +
          '<div id="fp-roster"></div></div></div>' +
          '<p class="panel-tip" style="margin-top:14px;max-width:760px;">Career totals, so a forward still checking off prime years can be outdrafted — that\'s the fun. Single-season scoring ships with a later slice. Rosters live in this browser.</p>',
        bind(view) {
          root = view;
          renderPresets();
          renderPool();
          renderRoster();
          view.querySelectorAll("[data-fp-tab]").forEach((b) =>
            b.addEventListener("click", () => {
              tab = b.dataset.fpTab;
              renderPool();
            })
          );
        },
      };
    } catch (err) {
      return "<div class='error-block'>" + HI_(err && err.message) + "</div>";
    }
  }

  function fmtF(v, role) {
    if (v == null) return "—";
    if (role === "goalie" && typeof v === "number" && !Number.isInteger(v)) return v.toFixed(3);
    return L(v);
  }

  /* ---------------- News ---------------- */
  async function news(ctx) {
    return {
      html:
        '<h1 class="page-title">News & Articles</h1>' +
        '<p class="page-sub">An original newsroom is planned — clean article cards, bookmarks, and writing by the local analyst. The feed source lands in a later slice.</p>' +
        '<div class="section" style="margin-top:26px;">' +
        '<div class="grid" style="grid-template-columns:repeat(3,1fr);">' +
        [0, 1, 2].map((i) =>
          '<div class="card" style="min-height:220px;display:flex;flex-direction:column;justify-content:space-between;">' +
          '<div><span class="eyebrow red">Editorial desk</span>' +
          '<h3 style="margin-top:10px;">' + (["The season ahead", "History repeats", "How leaders are really made"][i]) + "</h3>" +
          '<p class="muted" style="font-size:13px;">' + (["A data-driven look at what the countdown means.", "How franchise lineage survives relocation.", "Evidence, not vibes, behind the numbers."][i]) + "</p></div>" +
          '<span class="pill-tag">scheduled · later slice</span></div>'
        ).join("") +
        "</div></div>",
    };
  }

  /* ---------------- Favorites ---------------- */
  function normFav(f) {
    return {
      name: f.label || f.name || "Saved item",
      type: f.item_type || f.type || "player",
      id: f.item_key != null ? f.item_key : f.id,
      sub: f.sub || f.type || "",
    };
  }

  async function favorites(ctx) {
    const render = () => {
      const list = window.HI.favorites.list().map(normFav);
      return list.length
        ? '<div class="grid cards-xl">' +
          list.map((f) =>
            '<a href="' + hrefFor(f) + '" class="card hover" style="text-decoration:none;display:flex;align-items:center;gap:14px;">' +
            '<div style="width:46px;height:46px;border-radius:13px;background:linear-gradient(115deg,rgba(53,215,255,.16),rgba(122,162,255,.12));border:1px solid var(--line);display:grid;place-items:center;font-weight:800;color:var(--cyan);">' +
            HI_(window.HI.initials(f.name)) + "</div>" +
            '<div class="grow"><div style="font-weight:700;">' + HI_(f.name) + "</div>" +
            '<div class="muted" style="font-size:12px;">' + HI_(f.sub) + "</div></div>" +
            '<button class="btn sm ghost" data-rm="' + f.type + ":" + f.id + '" style="flex:none;">Remove</button></a>'
          ).join("") +
          "</div>"
        : '<div class="empty"><div class="glyph">☆</div><h4>Nothing saved yet</h4>' +
          "<p>Follow players, teams and franchises from any profile page and they will appear here.</p></div>";
    };

    return {
      html:
        '<h1 class="page-title">My Favorites</h1>' +
        '<p class="page-sub">' + (window.HI.account.token() ? "Synced to your account — follows follow you anywhere." : "Held locally in this browser. Sign in above to sync them across devices.") + "</p>" +
        '<div id="favorites-list">' + render() + "</div>",
      bind(view) {
        view.addEventListener("click", (e) => {
          const rm = e.target.closest("[data-rm]");
          if (!rm) return;
          const [type, id] = rm.dataset.rm.split(":");
          window.HI.favorites.remove({ type, id, name: "" });
          view.querySelector("#favorites-list").innerHTML = render();
          window.HI.toast("Removed from My Favorites");
        });
      },
    };
  }

  function hrefFor(f) {
    if (f.type === "player") return "#/players/" + f.id;
    if (f.type === "team") return "#/teams/" + f.id;
    if (f.type === "franchise") return "#/franchises/" + f.id;
    return "#/home";
  }

  /* ---------------- Settings ---------------- */
  const EVENT_KEYS = [
    ["preseason", "Preseason opens"],
    ["regular-season", "Regular season begins"],
    ["regular-season-end", "Regular season ends"],
    ["playoff-end", "Stanley Cup Final window"],
  ];

  async function settings(ctx) {
    const a = window.HI.account.get();
    const user = a && a.user ? a.user : null;
    const signedIn = !!window.HI.account.token();
    const facts = await window.HI.api("/api/season-facts").catch(() => null);
    const prefs = signedIn
      ? await window.HI.api("/api/account/prefs").catch(() => ({ prefs: [] }))
      : { prefs: [] };
    const prefSet = (prefs.prefs || []).filter((p) => p.enabled).map((p) => p.event_key);
    const leadDays = ((prefs.prefs || []).find((p) => p.enabled) || {}).lead_days || 3;
    const section = (ctx.query && ctx.query.section) || "";

    const profileHtml =
      '<div class="card" data-card="profile"><div class="head"><h3>Profile</h3>' +
      (signedIn ? '<span class="pill-tag cyan">server account</span>' : '<span class="pill-tag gold">this browser</span>') +
      "</div>" +
      (user
        ? '<p style="margin:0;"><b>' + HI_(user.display_name || user.username) + "</b><br/>" +
          '<span class="muted">@' + HI_(user.username) + "</span></p>" +
          '<button class="btn ghost" style="margin-top:12px;" id="settings-signout">Sign out</button>'
        : '<p class="muted" style="margin:0;">' +
          (signedIn ? "Account session starting…" : "No profile yet — favorites and prefs stay in this browser until you create one.") +
          "</p>" +
          '<button class="btn accent" style="margin-top:12px;" id="settings-account">' + (signedIn ? "Sign in again" : "Create profile") + "</button>") +
      "</div>";

    const prefsHtml =
      '<div class="card" data-card="prefs"><div class="head"><h3>Notification preferences</h3>' +
      (signedIn ? '<span class="pill-tag cyan">synced</span>' : '<span class="pill-tag gold">signed-in only</span>') +
      "</div>" +
      (signedIn
        ? '<p class="muted" style="font-size:13px;margin:0 0 10px;">Choose the league events you want a head-up on. We remind you as each one approaches — no fake news, only the platform calendar.</p>' +
          '<div class="row wrap">' +
          EVENT_KEYS.map(([key, label]) =>
            '<label class="pill-tag" style="cursor:pointer;user-select:none;">' +
            '<input type="checkbox" data-evkey="' + key + '"' + (prefSet.includes(key) ? " checked" : "") + ' style="accent-color:var(--cyan);"> ' +
            HI_(label) + "</label>"
          ).join("") +
          "</div>" +
          '<div class="row wrap" style="margin-top:14px;align-items:center;">' +
          '<span class="muted" style="font-size:12.5px;">Send heads-up</span>' +
          '<select id="prefs-lead" class="field" style="width:110px;">' +
          [1, 3, 7, 14].map((d) => '<option value="' + d + '"' + (d === leadDays ? " selected" : "") + ">" + d + " days</option>").join("") +
          "</select>" +
          '<button class="btn accent" id="prefs-save">Save preferences</button></div>'
        : '<p class="muted" style="margin:0;">Sign in to pick which league events surface in your notifications.</p>') +
      "</div>";

    return {
      html:
        '<h1 class="page-title">Settings</h1>' +
        '<p class="page-sub">Your account, notifications and local data. Synced preferences follow you across devices; nothing else leaves this machine.</p>' +
        '<div class="grid" style="grid-template-columns:1fr 1fr;align-items:start;">' +
        profileHtml + prefsHtml +
        "</div>" +
        '<div class="grid" style="grid-template-columns:1fr 1fr;align-items:start;margin-top:18px;">' +
        '<div class="card"><div class="head"><h3>Platform</h3></div>' +
        '<div class="factgrid" style="grid-template-columns:1fr 1fr;">' +
        '<div class="fact"><div class="k">Season start</div><div class="v">' + HI_((facts && facts.regular_season && facts.regular_season.start) || "—") + "</div></div>" +
        '<div class="fact"><div class="k">Teams</div><div class="v">' + L((facts && facts.league && facts.league.teams)) + "</div></div>" +
        '<div class="fact"><div class="k">Seasons tracked</div><div class="v">' + L((facts && facts.league && facts.league.seasons_tracked)) + "</div></div>" +
        '<div class="fact"><div class="k">Data source</div><div class="v">Embedded DB</div></div>' +
        "</div>" +
        '<p class="panel-tip" style="margin-top:12px;">The database is the source of truth. The UI never fabricates dates — countdowns derive from the league schedule API and configured calendar on the server.</p>' +
        "</div>" +
        '<div class="card"><div class="head"><h3>Local data</h3></div>' +
        '<div class="row wrap">' +
        '<button class="btn red" id="settings-clear">Clear favorites, watchlist, roster and local profile</button>' +
        "</div>" +
        '<p class="panel-tip" style="margin-top:12px;">Clearing local data keeps your server account untouched if you have one.</p>' +
        "</div></div>",
      bind(view) {
        if (section === "notification-prefs") {
          const card = view.querySelector("[data-card=prefs]");
          if (card) card.scrollIntoView({ block: "center", behavior: "smooth" });
        }
        const sa = view.querySelector("#settings-account");
        if (sa) sa.addEventListener("click", () => { (window.HI.$("#btn-account") || {}).click(); });
        const so = view.querySelector("#settings-signout");
        if (so) so.addEventListener("click", () => {
          const t = window.HI.account.token();
          window.HI.account.clear();
          if (t) window.HI.apiPost("/api/account/logout", {}).catch(() => {});
          window.HI.favorites.updateBadge();
          window.HI.toast("Signed out.");
          setTimeout(() => location.reload(), 400);
        });
        const psc = view.querySelector("#prefs-save");
        if (psc) psc.addEventListener("click", async () => {
          const keys = Array.from(view.querySelectorAll("[data-evkey]:checked")).map((c) => c.dataset.evkey);
          const lead = Number(view.querySelector("#prefs-lead").value);
          try {
            await window.HI.apiPost("/api/account/prefs", { event_keys: keys, lead_days: lead });
            window.HI.toast("Notification preferences saved.");
          } catch (err) {
            window.HI.toast((err && err.message) || "Could not save preferences.");
          }
        });
        view.querySelector("#settings-clear").addEventListener("click", () => {
          ["session", "favorites", "squad", "roster"].forEach((k) => localStorage.removeItem("hi." + k));
          window.HI.favorites.updateBadge();
          window.HI.toast("Local data cleared.");
          setTimeout(() => location.reload(), 400);
        });
      },
    };
  }

  window.HI_Schedule = schedule;
  window.HI_Events = events;
  window.HI_History = history;
  window.HI_Fantasy = fantasy;
  window.HI_News = news;
  window.HI_Favorites = favorites;
  window.HI_Settings = settings;
})();