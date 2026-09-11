/* ============================================================
   TEAMS + FRANCHISES
   ============================================================ */
(function () {
  "use strict";
  const HI_ = window.HI.escape;
  const L = window.HI.fmtNum;

  function logoTag(url, size) {
    return url
      ? '<img alt="" loading="lazy" src="' + HI_(url) + '" style="width:' + (size || 40) + 'px;height:' + (size || 40) + "px;object-fit:contain;\">"
      : "";
  }

  async function teams(ctx) {
    if (ctx.parts[1] && /^\d+$/.test(ctx.parts[1])) {
      return teamDetail(ctx);
    }
    try {
      const [tlist, st] = await Promise.all([
        window.HI.api("/api/teams"),
        window.HI.api("/api/standings?season_id=20242025&game_type=2").catch(() => null),
      ]);
      const byId = {};
      (st && st.rows || []).forEach((r) => { byId[r.team_id] = r; });

      const active = (tlist || []).filter((t) => t.active);
      const legacy = (tlist || []).filter((t) => !t.active);

      const card = (t) =>
        '<a href="#/teams/' + t.team_id + '" class="card tcard hover">' +
        '<span class="logo">' + logoTag(t.logo, 56) + "</span>" +
        '<span class="name">' + HI_(t.full_name) + "</span>" +
        '<span class="record">' + (byId[t.team_id]
          ? byId[t.team_id].points + " pts · " + byId[t.team_id].wins + "-" + byId[t.team_id].losses + (byId[t.team_id].ot_losses ? "-" + byId[t.team_id].ot_losses : "") + " (2024-25)"
          : HI_(t.abbreviation || "")) + "</span></a>";

      const html =
        '<h1 class="page-title">Teams</h1>' +
        '<p class="page-sub">Every club in the league, with its 2024-25 record pulled from the database. Individual franchises that moved or folded are preserved under Franchises.</p>' +
        '<div class="section"><div class="head"><h2>Current NHL clubs</h2><span class="pill-tag cyan">' + active.length + " teams</span></div>" +
        '<div class="grid cards-xl">' + active.map(card).join("") + "</div></div>" +
        (legacy.length
          ? '<div class="section"><div class="head"><h2>Retired / relocated</h2><span class="pill-tag gold">' + legacy.length + " clubs</span></div>" +
            '<div class="grid cards-xl">' + legacy.map(card).join("") + "</div></div>"
          : "");
      return { html };
    } catch (err) {
      return "<div class='error-block'>" + HI_(err && err.message) + "</div>";
    }
  }

  async function teamDetail(ctx) {
    const id = Number(ctx.parts[1]);
    try {
      const t = await window.HI.api("/api/teams/" + id);
      const seasonsData = await window.HI.api("/api/teams/" + id + "/seasons");
      const gamesInfo = await window.HI.api("/api/teams/" + id + "/games?limit=20").catch(() => null);
      const html =
        '<div class="card" style="margin-top:22px;">' +
        '<div class="row wrap" style="gap:20px;">' +
        '<div style="width:110px;height:110px;border-radius:22px;background:radial-gradient(circle at 30% 20%,#0f1a2b,#05080f);border:1px solid var(--line);display:grid;place-items:center;">' +
        logoTag(logoFromAbbr(t.abbreviation), 80) + "</div>" +
        '<div class="grow">' +
        '<span class="eyebrow">' + (t.active ? "NHL Club" : "Retired / relocated") + "</span>" +
        '<h1 style="font-size:clamp(24px,3.4vw,40px);font-weight:800;margin:4px 0;">' + HI_(t.full_name) + "</h1>" +
        '<div class="muted">' + HI_(t.abbreviation || "") + (t.franchise ? ' · <a href="#/franchises/' + t.franchise.id + '">' + HI_(t.franchise.name) + " franchise</a>" : "") + "</div>" +
        '<div class="row wrap" style="margin-top:14px;">' +
        window.HI.favBtn({ type: "team", id: t.team_id, name: t.full_name, sub: t.abbreviation || "Team" }) +
        '<a class="btn sm" href="#/ai?q=' + encodeURIComponent("Situation report on the " + t.full_name) + '">Ask AI</a>' +
        "</div></div></div></div>" +

        (t.championships && t.championships.length
          ? '<div class="section"><div class="head"><h2>Trophy cabinet</h2>' +
            '<span class="pill-tag gold">' + L(t.cup_count || 0) + " Stanley Cups</span></div>" +
            '<div class="card"><div class="row wrap" style="gap:8px;">' +
            t.championships.map((c) =>
              '<span class="chip">' + HI_(c.season_label) +
              (c.won ? " · <b>Champion</b>" : " · Finalist") +
              (c.runner_up ? ' · <span class="muted">vs ' + HI_(c.runner_up) + "</span>" : "") +
              "</span>"
            ).join("") +
            "</div></div></div>"
          : "") +

        seasonChartSection(
          seasonsData,
          "Season by season",
          (seasonsData.seasons || []).length + " seasons on record"
        ) +

        '<div class="section"><div class="head"><h2>Club history</h2></div>' +
        '<div class="card"><div class="timeline">' +
        (t.identities && t.identities.length
          ? t.identities.map((i) =>
              '<div class="tl-item"><div class="tl-date">' + HI_(i.start_year) + (i.end_year ? " — " + HI_(i.end_year) : " — present") + "</div>" +
              "<h4>" + HI_(i.city || "") + " " + HI_(i.name || "") + "</h4>" +
              "<p>" + HI_(i.abbr || "") + (i.notes ? " · " + HI_(i.notes) : "") + "</p></div>"
            ).join("")
          : '<div class="empty"><h4>No identity history recorded</h4><p>Identity rows will arrive with the deeper history slice.</p></div>') +
        "</div></div></div>" +

        gameLogSection(gamesInfo, id) +

        '<p class="panel-tip" style="margin-top:18px;">Season results are rebuilt from box scores on record; team streaks reflect every regular-season game, with OT and shootout losses treated as point-earning losses.</p>';
      return {
        html,
        bind() {
          const sel = document.getElementById("gl-season");
          if (sel) {
            sel.addEventListener("change", () => refreshGameLog(id, sel.value));
          }
        },
      };
    } catch (err) {
      return "<div class='error-block'>" + HI_(err && err.message) + "</div>";
    }
  }

  function logoFromAbbr(abbr) {
    return abbr ? "https://assets.nhle.com/logos/nhl/svg/" + abbr.toUpperCase() + "_light.svg" : null;
  }

  /* ---------------- Game log + game-level streaks ---------------- */

  function gameStreakChips(info) {
    const st = (info && info.streaks) || {};
    const chips = [];
    if (st.current_streak && st.current_streak.count) {
      const kind =
        st.current_streak.result === "W" ? "Wins" :
        st.current_streak.result === "OTL" ? "Point streak" : "Losses";
      chips.push({ label: "Current streak", value: kind + " " + st.current_streak.count });
    }
    if (st.longest_win_streak) chips.push({ label: "Longest win streak", value: st.longest_win_streak + " games" });
    if (st.longest_loss_streak) chips.push({ label: "Longest losing streak", value: st.longest_loss_streak + " games" });
    if (st.longest_point_streak) chips.push({ label: "Longest point streak", value: st.longest_point_streak + " games" });
    if (st.last_10) {
      chips.push({
        label: "Last 10",
        value: st.last_10.wins + (st.last_10.ot_losses ? "-" + st.last_10.ot_losses : "") + "-" + st.last_10.losses,
      });
    }
    if (st.wins != null) {
      chips.push({
        label: "Season",
        value: st.wins + (st.ot_losses ? "-" + st.ot_losses : "") + "-" + st.losses,
      });
    }
    return chips.length
      ? '<div class="row wrap" style="gap:8px;margin-bottom:14px;">' +
        chips.map((c) =>
          '<span class="chip"><span class="muted">' + HI_(c.label) + " · </span><b>" + HI_(c.value) + "</b></span>"
        ).join("") + "</div>"
      : '<div class="muted" style="margin-bottom:14px;">Regular-season game log loaded — no results yet.</div>';
  }

  function gameTableRows(games) {
    if (!games || !games.length) {
      return '<div class="empty"><h4>No games on record</h4><p>Results for this season have not been imported yet.</p></div>';
    }
    return games
      .slice()
      .reverse()
      .map((g) => {
        const badge = g.result ? ("<b class='" + (g.result === "W" ? "ok" : g.result === "OTL" ? "warn" : "bad") + "'>" + g.result + "</b>") : '<b class="muted">—</b>';
        const score = g.team_score != null && g.opponent_score != null
          ? g.team_score + "-" + g.opponent_score
          : "";
        const opp = g.opponent && g.opponent.name ? HI_(g.opponent.name) : "—";
        const home = g.is_home ? "vs" : "@";
        const ot = g.ot ? (g.ot === "OT" ? " OT" : " SO") : "";
        const date = (g.game_date || "").slice(0, 10);
        return (
          '<div class="gl-row">' +
          '<span class="gl-date muted">' + HI_(date) + "</span>" +
          "<span>" + badge + "</span>" +
          '<span class="gl-opp">' + home + " " + opp + "</span>" +
          '<span class="gl-score"><b>' + HI_(score) + "</b>" + (ot ? '<i class="muted">' + ot + "</i>" : "") + "</span>" +
          "<span class='gl-venue muted'>" + HI_(g.venue || "") + "</span>" +
          "</div>"
        );
      })
      .join("");
  }

  function gameLogSection(info, id) {
    if (!info || !info.games || !info.games.length) return "";
    const seasons = (info.coverage || [])
      .map(
        (c) =>
          '<option value="' + c.season_id + '"' +
          (Number(c.season_id) === Number(info.season_id) ? " selected" : "") + ">" +
          HI_(c.season_label) + " (" + L(c.games) + " games)</option>"
      )
      .join("");
    return (
      '<div class="section" id="gl-section"><div class="head">' +
      '<h2>Recent games</h2>' +
      '<span class="pill-tag cyan">Game log</span></div>' +
      '<div class="row wrap" style="align-items:center;gap:10px;margin-bottom:12px;">' +
      '<select class="field" id="gl-season" style="width:200px;height:38px;">' + seasons + "</select>" +
      "</div>" +
      '<div class="card"><div class="gl-list">' +
      gameStreakChips(info) +
      gameTableRows(info.games) +
      "</div></div></div>"
    );
  }

  async function refreshGameLog(id, seasonId) {
    const info = await window.HI.api("/api/teams/" + id + "/games?limit=30" + (seasonId ? "&season_id=" + seasonId : ""));
    const section = document.getElementById("gl-section");
    if (!section) return;
    section.innerHTML =
      '<div class="head"><h2>Recent games</h2><span class="pill-tag cyan">Game log</span></div>' +
      '<div class="row wrap" style="align-items:center;gap:10px;margin-bottom:12px;">' +
      '<select class="field" id="gl-season" style="width:200px;height:38px;">' +
      (info.coverage || []).map(
        (c) =>
          '<option value="' + c.season_id + '"' +
          (Number(c.season_id) === Number(info.season_id) ? " selected" : "") + ">" +
          HI_(c.season_label) + " (" + L(c.games) + " games)</option>"
      ).join("") +
      "</select></div>" +
      '<div class="card"><div class="gl-list">' +
      gameStreakChips(info) +
      gameTableRows(info.games) +
      "</div></div>";
    const sel = document.getElementById("gl-season");
    sel.addEventListener("change", () => refreshGameLog(id, sel.value));
  }

  /* ---------------- Season-by-season chart ---------------- */

  function seasonChartSection(seasonData, title, subtitle) {
    const seasons = (seasonData && seasonData.seasons) || [];
    if (!seasons.length) return "";
    const body = [];
    body.push(chartSvg(seasons));
    body.push(streakChips(seasonData));
    body.push(recordsRow(seasonData, seasons));
    return (
      '<div class="section"><div class="head"><h2>' + HI_(title) + "</h2>" +
      '<span class="pill-tag cyan">' + HI_(subtitle || "") + "</span></div>" +
      '<div class="card"><div class="chart-scroll">' + body.join("") + "</div></div></div>"
    );
  }

  function chartSvg(seasons) {
    const W = 1000, H = 300, padL = 34, padB = 30, padT = 24, padR = 12;
    const innerW = W - padL - padR, innerH = H - padT - padB;
    const maxPts = Math.max.apply(null, seasons.map((s) => s.points || 0));
    const scaleY = (v) => padT + innerH * (1 - (v || 0) / maxPts);
    const n = seasons.length;
    const step = innerW / Math.max(n, 1);
    const barW = Math.max(4, Math.min(26, step * 0.62));

    let bars = "",
        labels = "",
        markers = "";
    const labelEvery = Math.max(1, Math.ceil(n / 14));
    seasons.forEach((s, i) => {
      const x = padL + i * step + (step - barW) / 2;
      const y = scaleY(s.points);
      const h = padT + innerH - y;
      const gold = s.stanley_cup;
      const conf = s.conference_final && !s.stanley_cup;
      const tooltip =
        s.season_label + ": " + s.points + " pts · " + s.wins + "-" + s.losses +
        (s.ot_losses ? "-" + s.ot_losses : "") + (s.ties ? "-" + s.ties : "") +
        (gold ? " · CHAMPION" : conf ? " · conf. final" : "") +
        (s.cup_finalist && !gold ? " · Finalist" : "");
      bars +=
        '<g><title>' + HI_(tooltip) + "</title>" +
        '<rect x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + barW.toFixed(1) +
        '" height="' + Math.max(h, 1).toFixed(1) + '" rx="2" class="hbar' +
        (gold ? " hbar-cup" : conf ? " hbar-conf" : "") + '"></rect></g>';
      if (gold) {
        markers += '<text x="' + (padL + i * step).toFixed(1) +
          '" y="' + (scaleY(s.points) - 8).toFixed(1) +
          '" class="cup-mark" text-anchor="middle">★</text>';
      } else if (s.cup_finalist) {
        markers += '<circle cx="' + (padL + i * step).toFixed(1) +
          '" cy="' + (scaleY(s.points) - 6).toFixed(1) + '" r="3" class="finalist-mark"></circle>';
      }
      if (i % labelEvery === 0 || i === n - 1) {
        labels += '<text x="' + (padL + i * step).toFixed(1) +
          '" y="' + (H - 8).toFixed(1) + '" class="axis-label" text-anchor="middle">' +
          HI_(s.season_label) + "</text>";
      }
    });

    const maxLbl = maxPts;
    let grid = "";
    for (let v = 0; v <= 4; v++) {
      const val = Math.round((v / 4) * maxLbl);
      const y = scaleY(val);
      grid += '<line x1="' + padL + '" y1="' + y + '" x2="' + (W - padR) +
        '" y2="' + y + '" class="grid-line"></line>' +
        '<text x="' + (padL - 8) + '" y="' + (y + 4) +
        '" class="axis-label" text-anchor="end">' + val + "</text>";
    }

    return (
      '<div class="hchart"><svg viewBox="0 0 ' + W + " " + H +
      '" role="img" aria-label="Points by season">' +
      '<g>' + grid + "</g>" + "<g>" + bars + "</g>" + "<g>" + markers + "</g>" +
      "<g>" + labels + "</g></svg></div>" +
      '<div class="legend muted"><span><i class="dot cup"></i> Champion</span>' +
      '<span><i class="dot final"></i> Cup finalist</span>' +
      '<span><i class="dot conf"></i> Conference final</span></div>'
    );
  }

  function streakChips(seasonData) {
    const st = (seasonData && seasonData.streaks) || {};
    const chips = [
      { label: "Winning seasons run", value: st.current_winning_seasons === 1 ? "1 (current)" : (st.current_winning_seasons || "0") + " in a row" },
      { label: "Longest winning run", value: st.longest_winning_seasons || "0" },
      { label: "100-pt seasons run", value: (st.current_100_point_seasons || "0") + " in a row" },
    ];
    if (st.last_cup_season) {
      chips.push(
        st.seasons_since_cup === 0
          ? { label: "Reigning champion", value: "defending the cup" }
          : { label: "Cup drought", value: st.seasons_since_cup + " seasons" }
      );
    } else {
      chips.push({ label: "Cup history", value: "never won" });
    }
    return '<div class="row wrap" style="gap:8px;margin-bottom:14px;">' +
      chips.map((c) =>
        '<span class="chip"><span class="muted">' + HI_(c.label) + " · </span><b>" + HI_(c.value) + "</b></span>"
      ).join("") + "</div>";
  }

  function recordsRow(seasonData, seasons) {
    const rec = (seasonData && seasonData.records) || {};
    const fmt = (r) => (r ? r.season_label + " (" + r.value + (r.count > 1 ? ", x" + r.count : "") + ")" : "—");
    return (
      '<div class="row wrap" style="gap:8px;">' +
      '<span class="chip"><span class="muted">Most points · </span><b>' + HI_(fmt(rec.points)) + "</b></span>" +
      '<span class="chip"><span class="muted">Most wins · </span><b>' + HI_(fmt(rec.wins)) + "</b></span>" +
      '<span class="chip"><span class="muted">Best points% · </span><b>' + HI_(fmt(rec.points_pct)) + "</b></span>" +
      '<span class="chip"><span class="muted">Seasons on record · </span><b>' + seasons.length + "</b></span>" +
      "</div>"
    );
  }

  /* ---------------- Franchises ---------------- */
  async function franchises(ctx) {
    if (ctx.parts[1] && /^\d+$/.test(ctx.parts[1])) {
      return franchiseDetail(ctx);
    }
    try {
      const list = await window.HI.api("/api/franchises");
      const html =
        '<h1 class="page-title">Franchises</h1>' +
        '<p class="page-sub">The historical spine of the league — 40 franchises preserve every name, city and identity a club has carried, even after relocation or folding.</p>' +
        '<div class="grid cards-xl">' +
        list.map((f) =>
          '<a href="#/franchises/' + f.franchise_id + '" class="card hover" style="text-decoration:none;">' +
          '<div class="row" style="gap:12px;">' +
          '<div style="width:42px;height:42px;border-radius:12px;background:rgba(255,255,255,.05);border:1px solid var(--line);display:grid;place-items:center;font-weight:800;color:var(--cyan);">' +
          HI_(f.full_name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase()) + "</div>" +
          '<div class="grow"><div style="font-weight:700;">' + HI_(f.full_name) + "</div>" +
          '<div class="muted" style="font-size:12px;">Est. ' + HI_(f.established_year || "?") + "</div></div>" +
          '<span class="pill-tag" style="flex:none;">' + L(f.identity_count) + " identities</span>" +
          "</div></a>"
        ).join("") +
        "</div>";
      return { html };
    } catch (err) {
      return "<div class='error-block'>" + HI_(err && err.message) + "</div>";
    }
  }

  async function franchiseDetail(ctx) {
    const id = Number(ctx.parts[1]);
    try {
      const f = await window.HI.api("/api/franchises/" + id);
      const seasonsData = await window.HI.api("/api/franchises/" + id + "/seasons");
      const html =
        '<div class="card" style="margin-top:22px;">' +
        '<span class="eyebrow">Franchise · Est ' + HI_(f.established_year || "?") + "</span>" +
        '<h1 style="font-size:clamp(24px,3.4vw,40px);font-weight:800;margin:4px 0;">' + HI_(f.full_name) + "</h1>" +
        (f.notes ? '<p class="muted">' + HI_(f.notes) + "</p>" : "") +
        '<div class="row wrap" style="margin-top:12px;">' +
        window.HI.favBtn({ type: "franchise", id: f.franchise_id, name: f.full_name, sub: "Franchise" }) +
        "</div></div>" +

        '<div class="section"><div class="head"><h2>Identity timeline</h2></div>' +
        '<div class="card"><div class="timeline">' +
        (f.identities && f.identities.length
          ? f.identities.map((i) =>
              '<div class="tl-item"><div class="tl-date">' + HI_(i.start_year) + (i.end_year ? " — " + HI_(i.end_year) : " — present") + "</div>" +
              "<h4>" + HI_(i.city || "") + " " + HI_(i.name || "") + "</h4>" +
              '<p>' + HI_(i.abbr || "") +
              (i.team_id ? ' · <a href="#/teams/' + i.team_id + '">view club</a>' : "") +
              (i.notes ? " · " + HI_(i.notes) : "") + "</p></div>"
            ).join("")
          : '<div class="empty"><h4>No identities linked yet</h4><p>Identity rows arrive with the deeper history slice.</p></div>') +
        "</div></div></div>" +

        seasonChartSection(
          seasonsData,
          "Franchise history",
          (seasonsData.seasons || []).length + " seasons across the lineage"
        ) +
        "";
      return { html };
    } catch (err) {
      return "<div class='error-block'>" + HI_(err && err.message) + "</div>";
    }
  }

  window.HI_Teams = teams;
  window.HI_Franchises = franchises;
})();