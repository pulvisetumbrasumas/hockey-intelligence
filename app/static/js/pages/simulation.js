/* ============================================================
   SIMULATION — buy-then-play toy season
   Chances are game-level estimates from real rates; prices are
   made-up credits in a per-session budget. For fun, not betting.
   ============================================================ */
(function () {
  "use strict";
  const HI_ = window.HI.escape;
  const L = window.HI.fmtNum;
  const RESELL = 0.8;

  const HISTORY = 1; // placeholders kept minimal

  function pct(x) {
    return x == null ? "—" : Math.round(x * 100) + "%";
  }

  function bar(label, v, color) {
    const w = v == null ? 0 : Math.round(v * 100);
    return (
      '<div class="prob-row">' +
      '<span class="dim" style="font-size:11px;width:74px;flex:none;">' + HI_(label) + "</span>" +
      '<span class="track"><span style="width:' + w + "%;background:" + (color || "var(--gold)") + ';"></span></span>' +
      '<b class="num" style="width:36px;text-align:right;font-size:12px;">' + HI_(pct(v)) + "</b>" +
      "</div>"
    );
  }

  function card(kind, d, owned, onBuy) {
    const ownedTag = owned
      ? '<span class="pill-tag gold" style="font-size:9px;">owned</span>'
      : "";
    const why =
      kind === "skater"
        ? bar("points", d.probs.points, "var(--gold)") +
          bar("goals", d.probs.goals, "var(--red)") +
          bar("assists", d.probs.assists, "var(--cyan)") +
          bar("takeaways", d.probs.takeaways, "var(--purple)")
        : kind === "goalie"
          ? bar("shutout", d.probs.shutout, "var(--gold)") +
            bar("win", d.probs.win, "var(--cyan)")
          : bar("win", d.probs.win, "var(--gold)");
    const right =
      kind === "skater"
        ? '<span class="size"><b>' + L(d.goals) + "</b>G <b>" + L(d.assists) + "</b>A <b>" + L(d.points) + "</b>P</span>"
        : kind === "goalie"
          ? '<span class="size"><b>' + L(d.wins) + "</b>W <b>" + L(d.shutouts) + "</b>SO</span>"
          : '<span class="size">' + HI_(pct(d.win_pct)) + "</span>";
    return (
      '<div class="card sim-card' + (owned ? " owned" : "") + '">' +
      '<div class="row" style="justify-content:space-between;align-items:flex-start;gap:8px;">' +
      '<div class="grow">' +
      "<div class='row' style='gap:6px;align-items:center;'>" +
      '<b class="sim-name">' + HI_(d.name) + "</b>" + ownedTag + "</div>" +
      '<div class="dim" style="font-size:12px;margin-top:2px;">' + HI_(d.team || "—") + " · " + HI_(d.position || "T") + "</div></div>" +
      '<div class="price">' + L(d.price) + ' <span class="dim">cr</span></div>' +
      "</div>" +
      '<div class="sim-probs">' + why + "</div>" +
      '<div class="row" style="justify-content:space-between;align-items:center;margin-top:8px;">' +
      right +
      '<button class="btn sm ' + (owned ? "ghost" : "accent") + '" data-sim-buy>'
      + (owned ? "Resell (−20%)" : "Buy") + "</button>" +
      "</div></div>"
    );
  }

  async function simulation(ctx) {
    let tab = "skaters";
    let ui, shop, wallet, resultEl;

    const loadShop = async () => {
      try {
        shop = await window.HI.api("/api/simulation/shop");
      } catch (e) {
        return "<div class='error-block'>" + HI_(e && e.message || "shop unavailable") + "</div>";
      }
      const saved = window.HI.store.get("simulation", null);
      const fresh = !saved || saved.season !== shop.season;
      wallet = fresh
        ? { season: shop.season, skaters: [], goalies: [], teams: [] }
        : saved;
      if (fresh) window.HI.store.set("simulation", wallet);
      return null;
    };

    const budget = () =>
      shop.budget -
      wallet.skaters.reduce((a, x) => a + x.price, 0) -
      wallet.goalies.reduce((a, x) => a + x.price, 0) -
      wallet.teams.reduce((a, x) => a + x.price, 0);

    const has = (kind, id) =>
      wallet[kind].some((x) => String(x.id) === String(id));

    const buy = (kind, d) => {
      if (has(kind, d.player_id != null ? d.player_id : d.team_id)) {
        window.HI.toast("Already purchased.");
        return;
      }
      const delta = d.price;
      if (budget() - delta < 0) {
        window.HI.toast("Not enough credits — resell something first.");
        return;
      }
      wallet[kind].push({ id: d.player_id != null ? d.player_id : d.team_id, price: delta });
      window.HI.store.set("simulation", wallet);
      render();
      window.HI.toast(d.name + " purchased (−" + delta + " cr).");
    };

    const resell = (kind, id) => {
      const i = wallet[kind].findIndex((x) => String(x.id) === String(id));
      if (i < 0) return;
      const refund = Math.round(wallet[kind][i].price * RESELL);
      wallet[kind].splice(i, 1);
      window.HI.store.set("simulation", wallet);
      render();
      window.HI.toast("Resold for +" + refund + " cr.");
    };

    const render = () => {
      const list = shop[tab] || [];
      const idKey = (d) => String(d.player_id != null ? d.player_id : d.team_id);
      ui.querySelector("#sim-pool").innerHTML =
        '<div class="row wrap" style="gap:10px;flex:1;">' +
        list
          .map((d) => card(tab === "goalies" ? "goalie" : tab === "teams" ? "team" : "skater", d, has(tab === "goalies" ? "goalies" : tab === "teams" ? "teams" : "skaters", d.player_id != null ? d.player_id : d.team_id)))
          .join("") +
        "</div>";
      ui.querySelectorAll("#sim-pool [data-sim-buy]").forEach((b, idx) => {
        const d = list[idx];
        const kind = tab === "goalies" ? "goalies" : tab === "teams" ? "teams" : "skaters";
        b.addEventListener("click", () => {
          const owned = has(kind, d.player_id != null ? d.player_id : d.team_id);
          if (owned) resell(kind, d.player_id != null ? d.player_id : d.team_id);
          else buy(kind, d);
        });
      });
      renderWallet();
    };

    const renderWallet = () => {
      const n =
        wallet.skaters.length + wallet.goalies.length + wallet.teams.length;
      const el = ui.querySelector("#sim-budget");
      if (el) {
        el.textContent = budget() + " cr";
        el.style.color = budget() >= 10 ? "" : "var(--red)";
      }
      const play = ui.querySelector("#sim-play");
      if (play) play.disabled = n === 0;
      if (el && ui.querySelector("#sim-count")) ui.querySelector("#sim-count").textContent = n + " owned";
    };

    const play = async () => {
      const btn = ui.querySelector("#sim-play");
      btn.disabled = true;
      btn.textContent = "Simulating…";
      const body = {
        skaters: wallet.skaters.map((x) => x.id),
        goalies: wallet.goalies.map((x) => x.id),
        teams: wallet.teams.map((x) => x.id),
      };
      try {
        const res = await window.HI.apiPost("/api/simulation/season", body);
        renderResult(res);
        window.HI.store.set("simResult", res);
      } catch (e) {
        ui.querySelector("#sim-results").innerHTML =
          "<div class='error-block'>" + HI_(e && e.message) + "</div>";
      }
      btn.textContent = "Play the season again";
      btn.disabled = false;
    };

    const teamName = (r) =>
      (r.owned ? "● " : "") + r.name + " (" + r.abbreviation + ")";

    const renderResult = (res) => {
      const p = res.portfolio;
      const gainCls = p.gain >= 0 ? "pos" : "neg";
      const rows = res.standings
        .map(
          (r, i) =>
            '<tr class="' + (r.playoff ? "sim-playoff" : "") + (r.owned ? " sim-owned" : "") + '">' +
            "<td class='num'>" + (r.playoff ? "<b>" + r.rank + "</b>" : r.rank) + "</td>" +
            "<td>" + HI_(teamName(r)) + "</td>" +
            "<td class='num'>" + L(r.gp) + "</td>" +
            "<td class='num'>" + L(r.w) + "</td>" +
            "<td class='num'>" + L(r.l) + "</td>" +
            "<td class='num'>" + L(r.otl) + "</td>" +
            '<td class="num pts"><b>' + L(r.pts) + "</b></td>" +
            "<td class='num'>" + L(r.gf) + ":" + L(r.ga) + "</td>" +
            "<td class='num'>" + (r.diff >= 0 ? "+" : "") + L(r.diff) + "</td>" +
            "</tr>"
        )
        .join("");
      const stableRows = res.stable
        .map(
          (s) =>
            "<tr><td>" + HI_(s.name) + "</td><td>" + HI_(s.position || "—") + "</td>" +
            "<td>" + HI_(s.team) + "</td><td class='num'>" + L(s.gp) + "</td>" +
            "<td class='num'>" + L(s.goals) + "</td><td class='num'>" + L(s.assists) + "</td>" +
            "<td class='num pts'><b>" + L(s.points) + "</b></td><td class='num'>" + L(s.takeaways) + "</td></tr>"
        )
        .join("");
      const creaseRows = res.crease
        .map(
          (g) =>
            "<tr><td>" + HI_(g.name) + "</td><td>" + HI_(g.team) + "</td>" +
            "<td class='num'>" + L(g.gp) + "</td><td class='num'>" + L(g.wins) + "</td>" +
            "<td class='num pts'><b>" + L(g.shutouts) + "</b></td><td class='num'>" + L(g.goals_against) + "</td></tr>"
        )
        .join("");
      resultEl.innerHTML =
        '<div class="row wrap" style="gap:14px;margin-top:18px;">' +
        '<div class="card sim-port' + " " + gainCls + '">' +
        '<span class="eyebrow ' + (gainCls === "pos" ? "green" : "red") + '">Portfolio</span>' +
        '<h2 class="gain">' + (p.gain >= 0 ? "+" : "−") + Math.abs(p.gain).toFixed(1) + " cr</h2>" +
        '<div class="dim">value ' + p.value.toFixed(1) + " · spent " + p.spent.toFixed(1) + " · " +
        "balance " + p.balance.toFixed(1) + " (budget " + p.budget + ")</div>" +
        "<div class='dim' style='font-size:11px;margin-top:4px;'>" +
        "skater pt = 0.35 cr · goalie win = 1.2 cr · shutout = 2.5 cr · team win = 0.8 cr</div>" +
        "</div>" +
        '<div class="card sim-port">' +
        "<span class='eyebrow'>Season</span>" +
        "<h2>" + (res.standings[0] ? res.standings[0].name : "—") + '</h2>' +
        '<div class="dim">regular-season leader · ' + res.standings.length + " clubs · " +
        res.games_per_team + " GP each</div>" +
        "</div></div>" +

        '<div class="section">' +
        '<div class="head"><h3>Standings</h3><span class="dim" style="font-size:11px;">playoff line = top 8</span></div>' +
        '<div style="overflow-x:auto;"><table class="dtable">' +
        "<thead><tr><th>#</th><th>Team</th><th>GP</th><th>W</th><th>L</th><th>OT</th><th>PTS</th><th>GF:GA</th><th>Diff</th></tr></thead>" +
        "<tbody>" + rows + "</tbody></table></div></div>" +

        (res.stable.length
          ? '<div class="section"><div class="head"><h3>Your skaters</h3></div>' +
            '<div style="overflow-x:auto;"><table class="dtable"><thead><tr><th>Player</th><th>Pos</th><th>Team</th><th>GP</th><th>G</th><th>A</th><th>PTS</th><th>TK</th></tr></thead>' +
            "<tbody>" + stableRows + "</tbody></table></div></div>"
          : "") +

        (res.crease.length
          ? '<div class="section"><div class="head"><h3>Your goaltenders</h3></div>' +
            '<div style="overflow-x:auto;"><table class="dtable"><thead><tr><th>Player</th><th>Team</th><th>GP</th><th>W</th><th>SO</th><th>GA</th></tr></thead>' +
            "<tbody>" + creaseRows + "</tbody></table></div></div>"
          : "") +

        '<p class="panel-tip">' + HI_(res.note) + "</p>" +
        '<p class="dim" style="font-size:11px;">played ' + HI_(String(res.ran_at).slice(0, 19).replace("T", " ")) + " UTC · " + res.season + "</p>";
    };

    const boot = await loadShop();
    if (boot) return boot;

    const prior = window.HI.store.get("simResult", null);
    const html =
      '<h1 class="page-title">Season Simulation</h1>' +
      '<p class="page-sub">Buy players and teams with a fixed credit budget, then play a compressed regular season. Player chances are game-level estimates from last season’s real rates — points, goals, assists, takeaways, shutouts, team wins. Priced for fun, not for betting.</p>' +
      '<div class="row wrap" style="gap:10px;align-items:center;margin-bottom:14px;">' +
      '<span class="pill-tag gold" id="sim-budget">' + shop.budget + " cr</span>" +
      '<span class="pill-tag" id="sim-count">0 owned</span>' +
      '<button class="btn accent" id="sim-play">Play the season</button>' +
      '<span class="dim" style="font-size:12px;">' + shop.games_per_team + " GP · " + shop.season + "</span></div>" +

      '<div class="row wrap" style="gap:8px;margin-bottom:12px;">' +
      '<button class="btn sm ghost" data-sim-tab="skaters">Skaters</button>' +
      '<button class="btn sm ghost" data-sim-tab="goalies">Goalies</button>' +
      '<button class="btn sm ghost" data-sim-tab="teams">Teams</button></div>' +
      '<div id="sim-pool"></div>' +
      '<div id="sim-results"></div>';

    const model = {
      html,
      bind(view) {
        ui = view;
        resultEl = view.querySelector("#sim-results");
        if (prior) renderResult(prior);
        render();
        view.querySelectorAll("[data-sim-tab]").forEach((b) =>
          b.addEventListener("click", () => {
            tab = b.dataset.simTab;
            view.querySelectorAll("[data-sim-tab]").forEach((x) =>
              x.classList.toggle("accent", x === b)
            );
            render();
          })
        );
        view.querySelector("#sim-play").addEventListener("click", play);
      },
    };
    return model;
  }

  window.HI_Simulation = simulation;
})();