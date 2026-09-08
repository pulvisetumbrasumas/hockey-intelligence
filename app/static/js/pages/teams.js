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

        '<p class="panel-tip" style="margin-top:18px;">Team headshots, schedules and in-season results stream in later slices. Franchise lineage lives under Franchises.</p>';
      return { html };
    } catch (err) {
      return "<div class='error-block'>" + HI_(err && err.message) + "</div>";
    }
  }

  function logoFromAbbr(abbr) {
    return abbr ? "https://assets.nhle.com/logos/nhl/svg/" + abbr.toUpperCase() + "_light.svg" : null;
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
        "</div></div></div>";
      return { html };
    } catch (err) {
      return "<div class='error-block'>" + HI_(err && err.message) + "</div>";
    }
  }

  window.HI_Teams = teams;
  window.HI_Franchises = franchises;
})();