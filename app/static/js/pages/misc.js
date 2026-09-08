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

  /* ---------------- Fantasy (experimental shell) ---------------- */
  async function fantasy(ctx) {
    try {
      const [skaters, wins, spct] = await Promise.all([
        window.HI.api("/api/stats/leaders/career?metric=points&stat_type=skater&limit=16"),
        window.HI.api("/api/stats/leaders/career?metric=wins&stat_type=goalie&limit=8"),
        window.HI.api("/api/stats/leaders/career?metric=save_pct&stat_type=goalie&limit=8"),
      ]);
      const pick = (d) => d.results || d.rows || [];
      const all = [
        ...pick(skaters).map((r) => ({ ...r, role: "skater" })),
        ...pick(wins).map((r) => ({ ...r, role: "goalie" })),
        ...pick(spct).map((r) => ({ ...r, role: "goalie" })),
      ];
      return {
        html:
          '<h1 class="page-title">Fantasy</h1>' +
          '<p class="page-sub"><b>Experimental, for fun</b> — this is a taste of the draft room, not a prediction engine. Build a watchlist from real career leaders; fantasy scoring is entertainment, never a claim about who is objectively best.</p>' +
          '<div class="card">' +
          '<div class="head"><h3>Draft room (preview)</h3><span class="pill-tag gold">simulation</span></div>' +
          '<p class="muted" style="font-size:13px;">Tap leaders to add them to your watchlist. Full fantasy wiring — scoring systems, leagues, drafts — lands in a later slice.</p>' +
          '<div class="row wrap" style="gap:8px;margin:14px 0;" id="squad"></div>' +
          '<div style="max-height:380px;overflow-y:auto;border:1px solid var(--line);border-radius:10px;">' +
          all.map((r, i) =>
            '<div class="row fantasy-row" data-pid="' + r.player_id + '" style="padding:8px 12px;cursor:pointer;border-bottom:1px solid var(--line-soft);">' +
            '<span class="rank" style="width:22px;height:22px;border-radius:6px;display:grid;place-items:center;font-size:11px;font-weight:700;background:rgba(255,255,255,.05);color:var(--text-3);">' + (i + 1) + "</span>" +
            '<span class="grow" style="font-weight:600;">' + HI_(r.full_name) + "</span>" +
            '<span class="pill-tag ' + (r.role === "goalie" ? "gold" : "cyan") + '" style="font-size:9px;">' + (r.role || "") + "</span>" +
            '<span class="num" style="color:var(--cyan);font-weight:700;">' + fmtF(r.value, r.role) + "</span></div>"
          ).join("") +
          "</div>" +
          '<div class="row wrap" style="margin-top:14px;">' +
          '<button class="btn accent" id="squad-save">Save watchlist</button>' +
          '<button class="btn ghost" id="squad-clear">Clear</button></div>' +
          "<p class='panel-tip' style='margin-top:12px;'>Watchlists live in this browser. Verified by the same statistics engine that runs this whole platform.</p>" +
          "</div>",
        bind(view) {
          let squad = window.HI.store.get("hi.squad", []);
          const box = view.querySelector("#squad");
          const renderSquad = () => {
            box.innerHTML = squad.length
              ? squad.map((p) =>
                  '<span class="pill-tag cyan">' + HI_(p.full_name) + '<b style="cursor:pointer;" data-x="' + p.player_id + '"> ×</b></span>'
                ).join("")
              : '<span class="dim">No players selected yet.</span>';
            box.querySelectorAll("[data-x]").forEach((b) =>
              b.addEventListener("click", () => {
                squad = squad.filter((p) => String(p.player_id) !== String(b.dataset.x));
                window.HI.store.set("squad", squad);
                renderSquad();
              })
            );
          };
          renderSquad();
          view.querySelectorAll(".fantasy-row").forEach((row) => {
            row.addEventListener("click", () => {
              const pid = row.dataset.pid;
              const name = row.querySelector(".grow").textContent;
              if (squad.some((p) => String(p.player_id) === pid)) {
                squad = squad.filter((p) => String(p.player_id) !== pid);
                window.HI.toast("Removed from watchlist.");
              } else {
                squad.push({ player_id: pid, full_name: name });
                window.HI.store.set("squad", squad);
                window.HI.toast("Added to watchlist.");
              }
              renderSquad();
            });
          });
          view.querySelector("#squad-save").addEventListener("click", () => {
            window.HI.store.set("squad", squad);
            window.HI.toast("Watchlist saved (" + squad.length + " players).");
          });
          view.querySelector("#squad-clear").addEventListener("click", () => {
            squad = [];
            window.HI.store.set("squad", []);
            renderSquad();
          });
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
  async function favorites(ctx) {
    const list = window.HI.favorites.list();
    const render = () =>
      list.length
        ? '<div class="grid cards-xl">' +
          list.map((f) =>
            '<a href="' + hrefFor(f) + '" class="card hover" style="text-decoration:none;display:flex;align-items:center;gap:14px;">' +
            '<div style="width:46px;height:46px;border-radius:13px;background:linear-gradient(115deg,rgba(53,215,255,.16),rgba(122,162,255,.12));border:1px solid var(--line);display:grid;place-items:center;font-weight:800;color:var(--cyan);">' +
            HI_(window.HI.initials(f.name)) + "</div>" +
            '<div class="grow"><div style="font-weight:700;">' + HI_(f.name) + "</div>" +
            '<div class="muted" style="font-size:12px;">' + HI_(f.sub || f.type) + "</div></div>" +
            '<button class="btn sm ghost" data-rm="' + f.type + ":" + f.id + '" style="flex:none;">Remove</button></a>'
          ).join("") +
          "</div>"
        : '<div class="empty"><div class="glyph">☆</div><h4>Nothing saved yet</h4>' +
          "<p>Follow players, teams and franchises from any profile page and they will appear here.</p></div>";

    return {
      html:
        '<h1 class="page-title">My Favorites</h1>' +
        '<p class="page-sub">Your saved follows, held locally in this browser for now.</p>' +
        '<div id="favorites-list">' + render() + "</div>",
      bind(view) {
        view.addEventListener("click", (e) => {
          const rm = e.target.closest("[data-rm]");
          if (!rm) return;
          const [type, id] = rm.dataset.rm.split(":");
          const next = window.HI.favorites.list().filter(
            (f) => !(f.type === type && String(f.id) === id)
          );
          window.HI.store.set("favorites", next);
          window.HI.favorites.updateBadge();
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
  async function settings(ctx) {
    const a = window.HI.account.get();
    const facts = await window.HI.api("/api/season-facts").catch(() => null);
    return {
      html:
        '<h1 class="page-title">Settings</h1>' +
        '<p class="page-sub">Local preferences for this browser. Server-backed accounts and sync arrive in a later vertical slice.</p>' +
        '<div class="grid" style="grid-template-columns:1fr 1fr;align-items:start;">' +
        '<div class="card"><div class="head"><h3>Profile</h3></div>' +
        (a
          ? '<p style="margin:0;"><b>' + HI_(a.name) + "</b><br/><span class='muted'>" + HI_(a.email || "no email") + "</span></p>" +
            '<button class="btn ghost" style="margin-top:12px;" id="settings-signout">Sign out</button>'
          : '<p class="muted" style="margin:0;">No profile yet.</p>' +
            '<button class="btn accent" style="margin-top:12px;" id="settings-account">Create profile</button>') +
        "</div>" +
        '<div class="card"><div class="head"><h3>Platform</h3></div>' +
        '<div class="factgrid" style="grid-template-columns:1fr 1fr;">' +
        '<div class="fact"><div class="k">Season start</div><div class="v">' + HI_((facts && facts.regular_season && facts.regular_season.start) || "—") + "</div></div>" +
        '<div class="fact"><div class="k">Teams</div><div class="v">' + L((facts && facts.league && facts.league.teams)) + "</div></div>" +
        '<div class="fact"><div class="k">Seasons tracked</div><div class="v">' + L((facts && facts.league && facts.league.seasons_tracked)) + "</div></div>" +
        '<div class="fact"><div class="k">Data source</div><div class="v">Embedded DB</div></div>' +
        "</div>" +
        '<p class="panel-tip" style="margin-top:12px;">The database is the source of truth. The UI never fabricates dates — countdowns derive from the league schedule API and configured calendar on the server.</p>' +
        "</div></div>" +
        '<div class="card" style="margin-top:18px;"><div class="head"><h3>Local data</h3></div>' +
        '<div class="row wrap">' +
        '<button class="btn red" id="settings-clear">Clear favorites, watchlist and profile</button>' +
        "</div></div>",
      bind(view) {
        const sa = view.querySelector("#settings-account");
        if (sa) sa.addEventListener("click", () => { (window.HI.$("#btn-account") || {}).click(); });
        const so = view.querySelector("#settings-signout");
        if (so) so.addEventListener("click", () => { window.HI.account.clear(); window.HI.toast("Signed out."); setTimeout(() => location.reload(), 400); });
        view.querySelector("#settings-clear").addEventListener("click", () => {
          ["account", "favorites", "squad"].forEach((k) => localStorage.removeItem("hi." + k));
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