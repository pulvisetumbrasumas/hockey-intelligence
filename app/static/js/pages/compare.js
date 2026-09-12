/* ============================================================
   COMPARE — multi-player evidence radar
   ============================================================ */
(function () {
  "use strict";
  const HI_ = window.HI.escape;
  const L = window.HI.fmtNum;

  const COLORS = ["#35d7ff", "#9f7bff", "#f5c36b", "#ff4d5e", "#69e0a0"];

  async function compare(ctx) {
    try {
      const prefill = (ctx.hashNoHash ? ctx.hashNoHash.split("?")[1] : location.hash.split("?")[1]) || "";
      const params = new URLSearchParams(prefill);
      const seed = params.get("p");

      const html =
        '<h1 class="page-title">Compare players</h1>' +
        '<p class="page-sub">Drop two to five players in and the tool renders evidence-based profiles per dimension. <b>No single winner is declared</b> — different players shine on different axes.</p>' +
        '<div class="card" style="margin-bottom:20px;">' +
        '<div class="head"><h3>Roster</h3>' +
        '<button class="btn sm" id="add-ply">+ Add player</button></div>' +
        '<div id="player-slots"></div>' +
        '<div class="row wrap" style="margin-top:14px;">' +
        '<button class="btn accent" id="run-compare">Compare</button>' +
        "</div></div>" +

        '<div id="compare-out"></div>';

      return {
        html,
        bind(view) {
          const slots = view.querySelector("#player-slots");
          const pickers = [];
          let active = -1;

          function slotHtml(pick) {
            return (
              '<div class="multi" style="margin-bottom:10px;position:relative;">' +
              '<input class="field" data-slot placeholder="Type a player name…" value="' + HI_(pick || "") + '" />' +
              '<div class="search-drop hidden" data-slotdrop></div>' +
              '<button class="btn sm ghost" data-slotx style="position:absolute;right:6px;top:5px;">✕</button>' +
              "</div>"
            );
          }

          function refreshCount() {
            const count = slots.children.length;
            const rm = slots.querySelectorAll("[data-slotx]");
            rm.forEach((b) => { b.classList.toggle("hidden", count <= 2); });
          }

          function addSlot(pick) {
            const div = document.createElement("div");
            div.innerHTML = slotHtml(pick || "");
            const node = div.firstChild;
            slots.appendChild(node);
            wire(node, pick);
            refreshCount();
          }

          function wire(el, initialName) {
            const input = el.querySelector("[data-slot]");
            const drop = el.querySelector("[data-slotdrop]");
            let timer = null;
            let opts = [];

            const close = () => drop.classList.add("hidden");
            input.addEventListener("input", () => {
              clearTimeout(timer);
              const q = input.value.trim();
              if (q.length < 2) { close(); return; }
              timer = setTimeout(async () => {
                try {
                  const data = await window.HI.api("/api/search?q=" + encodeURIComponent(q) + "&limit=5");
                  opts = (data.players || []);
                  if (!opts.length) { close(); return; }
                  drop.innerHTML = opts.map((p, i) =>
                    '<div class="search-item" data-i="' + i + '">' +
                    '<img alt="" src="' + HI_(p.headshot || "") + '" onerror="this.style.display=\'none\'">' +
                    '<span class="grow"><span class="lead">' + HI_(p.full_name) + "</span>" +
                    ' <span class="sub">' + HI_(p.position || "") + "</span></span></div>"
                  ).join("");
                  drop.classList.remove("hidden");
                  active = -1;
                } catch (_) { close(); }
              }, 220);
            });
            drop.addEventListener("mousedown", (e) => {
              const item = e.target.closest(".search-item");
              if (!item) return;
              const p = opts[Number(item.dataset.i)];
              if (!p) return;
              input.value = p.full_name;
              input.dataset.pid = String(p.player_id);
              close();
            });
            input.addEventListener("keydown", (e) => {
              if (e.key === "Escape") close();
              if (e.key === "Enter") {
                e.preventDefault();
                const q = input.value.trim();
                const match = opts.find((o) => o.full_name.toLowerCase() === q.toLowerCase());
                if (match) { input.value = match.full_name; input.dataset.pid = String(match.player_id); close(); }
              }
            });
            el.querySelector("[data-slotx]").addEventListener("click", () => {
              el.remove();
              refreshCount();
              if (slots.children.length === 0) addSlot();
              pickers.splice(pickers.indexOf(el), 1);
            });
            if (initialName) {
              setTimeout(async () => {
                try {
                  const data = await window.HI.api("/api/search?q=" + encodeURIComponent(initialName) + "&limit=5");
                  const match = (data.players || []).find((p) => String(p.player_id) === seed) || data.players[0];
                  if (match) { input.value = match.full_name; input.dataset.pid = String(match.player_id); }
                } catch (_) {}
              }, 50);
            }
          }

          addSlot(seed ? null : "Connor McDavid");
          addSlot(null);
          if (seed) { const first = slots.querySelector("[data-slot]"); first.value = ""; first.dataset.pid = ""; wire(slots.children[0], ""); }

          view.querySelector("#add-ply").addEventListener("click", () => {
            if (slots.children.length >= 5) { window.HI.toast("Maximum of five players."); return; }
            addSlot();
          });

          document.addEventListener("click", (e) => {
            if (!e.target.closest(".multi")) {
              slots.querySelectorAll("[data-slotdrop]").forEach((d) => d.classList.add("hidden"));
            }
          });

          view.querySelector("#run-compare").addEventListener("click", async () => {
            const ids = [];
            slots.querySelectorAll("[data-slot]").forEach((inp) => {
              const pid = parseInt(inp.dataset.pid, 10);
              if (pid) ids.push(pid);
            });
            if (ids.length < 2) { window.HI.toast("Add at least two players."); return; }
            const out = view.querySelector("#compare-out");
            out.innerHTML = '<div class="loading-block"><div class="spinner"></div>Computing comparison…</div>';
            try {
              const q = ids.map((x) => "player_ids=" + x).join("&");
              const res = await window.HI.apiPost("/api/compare/players?" + q);
              out.innerHTML = renderComparison(res);
              drawRadar(res, out.querySelector("#radar"));
            } catch (err) {
              out.innerHTML = "<div class='error-block'>" + HI_(err && err.message) + "</div>";
            }
          });
        },
      };
    } catch (err) {
      return "<div class='error-block'>" + HI_(err && err.message) + "</div>";
    }
  }

  function renderComparison(res) {
    const players = res.players || [];
    const fmt = (v) =>
      v == null || v === "" ? "<span class='dim'>—</span>"
      : Number.isInteger(v) ? L(v)
      : L(Number(v.toFixed(3)));

    const LABELS = {
      offense: "Offense", two_way: "Two-way", defense: "Two-way",
      puck_skill: "Puck skill", efficiency: "Efficiency", durability: "Durability",
    };
    const META = [
      ["games_played", "Games played"],
      ["points", "Points"],
      ["era_adjusted_points", "Era-adjusted points"],
      ["pace_points_82", "Pace (pts / 82)"],
      ["points_per_game", "Points per game"],
      ["plus_minus", "Plus/minus"],
      ["seasons_played", "Seasons played"],
    ];

    const metaRow = (m, label) =>
      "<tr><td>" + HI_(label) + "</td>" +
      players.map((p) => "<td class='num'>" + fmt(p[m]) + "</td>").join("") +
      "</tr>";

    const header = "<thead><tr><th>Metric</th>" +
      players.map((p) => "<th class='num'>" + HI_(p.name) + "</th>").join("") +
      "</tr></thead>";

    function evidenceRow(m, label, ev) {
      const values = (ev.values && ev.values[m]) || {};
      return "<tr><td>" + HI_(label) + "</td>" +
        players.map((p) => "<td class='num'>" + fmt(values[p.player_id]) + "</td>").join("") +
        "</tr>";
    }

    const dimsBlocks = (res.dimensions || []).map((d) => {
      const ev = (res.evidence && res.evidence[d]) || {};
      const skip = new Set(["era_adjusted_points", "points_per_game", "era_adjusted_ppg",
        "goals", "assists", "points", "games_played", "seasons_played"]);
      const rows = (ev.metric || [])
        .filter((m) => !skip.has(m))
        .map((m) => evidenceRow(m, m.replace(/_/g, " "), ev))
        .join("");
      if (!rows) return "";
      return "<tr class='dim-cap'><td colspan='" + (players.length + 1) + "'>" +
        "<b style='color:var(--cyan);'>" + HI_(LABELS[d] || d) + "</b></td></tr>" + rows;
    }).join("");

    const table = "<table class='dtable'>" + header + "<tbody>" +
      META.map(([m, label]) => metaRow(m, label)).join("") +
      dimsBlocks + "</tbody></table>";

    const era = res.era ? '<p class="panel-tip" style="margin:10px 0 0;">' + HI_(res.era.note) + "</p>" : "";
    const dataNotes = (res.data_notes || []).map((n) =>
      '<p class="panel-tip" style="margin:8px 0 0;">' + HI_(n) + "</p>"
    ).join("");
    const notes = (res.notes || []).length
      ? '<p class="panel-tip" style="margin:12px 0;">' + res.notes.map(HI_).join(" ") + "</p>"
      : "";

    return (
      '<div class="grid" style="grid-template-columns:minmax(300px,380px) 1fr;align-items:start;">' +
      '<div class="card"><h3>Dimension radar</h3>' +
      '<div class="radar-wrap"><canvas id="radar" width="320" height="320"></canvas></div>' +
      '<div style="margin-top:6px;" id="radar-legend"></div>' +
      '<p class="panel-tip" style="margin-top:12px;">Each axis is a dimension. Within an axis, every metric is scaled against the group so mixed units do not skew the shape; missing data omits that metric.</p>' +
      "</div>" +
      '<div class="stack">' +
      '<div class="card"><h3>Career evidence</h3>' + table + era + dataNotes + notes + "</div>" +
      '<div class="card"><h3>How to read this</h3>' +
      "<p style='margin:0;font-size:13.5px;color:var(--text-2);'>" +
      (res.dimensions || []).map((d) => {
        const ev = (res.evidence && res.evidence[d]) || {};
        return "<div style='margin-bottom:10px;'><b style='color:var(--cyan);text-transform:capitalize;'>" + HI_(LABELS[d] || d) + "</b> — " +
          HI_(ev.interpretation || "") + "</div>";
      }).join("") +
      "</p></div>" +
      "</div></div>"
    );
  }

  function drawRadar(res, canvas) {
    if (!canvas) return;
    const players = res.players || [];
    const evidence = res.evidence || {};
    const dims = (res.dimensions || []).filter((d) => {
      const ev = evidence[d] || {};
      return players.some((p) => (ev.values ? someValue(ev, d, p) : false));
    });
    if (!dims.length) { return; }

    /* normalized 0..100 score per player per dimension.
       Within each dimension every metric is scaled against the group's best
       before averaging, so mixed units (points totals vs points-per-game) do
       not distort the shape; metrics without usable data are skipped. */
    const scores = {};
    players.forEach((p) => {
      scores[p.player_id] = {};
      dims.forEach((d) => {
        const ev = evidence[d] || {};
        const comps = Object.keys(ev.values || {}).filter((m) =>
          players.some((q) => ev.values[m] && ev.values[m][q.player_id] != null));
        if (!comps.length) { scores[p.player_id][d] = 0; return; }
        let acc = 0, n = 0;
        comps.forEach((m) => {
          const vals = ev.values[m];
          const mx = Math.max.apply(null, players.map((q) =>
            vals[q.player_id] != null ? Number(vals[q.player_id]) : -Infinity));
          if (!(mx > 0)) return;
          const v = vals[p.player_id];
          if (v == null) return;
          acc += Math.max(0, Number(v)) / mx;
          n += 1;
        });
        scores[p.player_id][d] = n ? Math.round((acc / n) * 100) : 0;
      });
    });

    const ctx = canvas.getContext("2d");
    const W = canvas.width, H = canvas.height;
    const cx = W / 2, cy = H / 2 + 6, R = Math.min(W, H) / 2 - 34;
    const N = dims.length;
    if (N < 3) {
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = "rgba(255,255,255,.5)";
      ctx.font = "13px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Not enough axes to draw a radar.", cx, cy);
      return;
    }
    const ang = (i) => -Math.PI / 2 + (i * 2 * Math.PI) / N;
    const pt = (i, r) => [cx + Math.cos(ang(i)) * r, cy + Math.sin(ang(i)) * r];

    ctx.clearRect(0, 0, W, H);

    /* rings */
    for (let ring = 1; ring <= 4; ring++) {
      ctx.beginPath();
      for (let i = 0; i <= N; i++) {
        const [x, y] = pt(i % N, (R * ring) / 4);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.strokeStyle = "rgba(224,242,255,.08)";
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    /* spokes + labels */
    ctx.font = "12px 'Inter',sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    dims.forEach((d, i) => {
      const [x, y] = pt(i, R + 18);
      ctx.fillStyle = "#bfd9f5";
      ctx.fillText(d.replace(/_/g, " "), x, y);
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(...pt(i, R));
      ctx.strokeStyle = "rgba(224,242,255,.07)";
      ctx.stroke();
    });

    players.forEach((p, pidx) => {
      const color = COLORS[pidx % COLORS.length];
      ctx.beginPath();
      for (let i = 0; i <= N; i++) {
        const r = ((scores[p.player_id][dims[i % N]] || 0) / 100) * R;
        const [x, y] = pt(i % N, r);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.globalAlpha = 0.28;
      ctx.fillStyle = color;
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.shadowColor = color;
      ctx.shadowBlur = 8;
      ctx.stroke();
      ctx.shadowBlur = 0;
      players.forEach((q, qi) => {
        const [x, y] = pt(qi, ((scores[p.player_id][dims[qi]] || 0) / 100) * R);
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
      });
    });

    /* legend */
    const legend = document.getElementById("radar-legend");
    if (legend) {
      legend.innerHTML = players.map((p, i) =>
        '<span style="display:inline-flex;align-items:center;gap:7px;margin:0 12px 6px 0;font-size:12.5px;color:var(--text-2);">' +
        '<span style="width:12px;height:12px;border-radius:3px;background:' + COLORS[i % COLORS.length] + ';box-shadow:0 0 8px rgba(53,215,255,.4);"></span>' +
        HI_(p.name) + "</span>"
      ).join("");
    }
  }

  function someValue(ev, dim, p) {
    return Object.values(ev.values || {}).some((m) => m[p.player_id] != null);
  }

  window.HI_Compare = compare;
})();