/* ============================================================
   AI HOCKEY ANALYST — local, database-grounded chat
   ============================================================ */
(function () {
  "use strict";
  const HI_ = window.HI.escape;

  async function aiPage(ctx) {
    const q = new URLSearchParams((ctx.hashNoHash || location.hash).split("?")[1] || "").get("q") || "";
    const html =
      '<div class="section" style="margin-top:24px;">' +
      '<div class="head">' +
      "<div><span class='eyebrow'>Local reasoning</span>" +
      '<h1 class="page-title" style="margin:2px 0 4px;">AI Hockey Analyst</h1></div>' +
      '<span class="pill-tag cyan" id="ai-status">checking</span></div>' +
      '<p class="page-sub">Ollama runs entirely on this machine. It plans a query, resolves verified facts from the database through tools, then explains what the data shows. It cannot invent numbers — every figure is traceable in the panel.</p>' +
      '<div class="card">' +
      '<div class="chat" id="chat"></div>' +
      '<div class="chat-input">' +
      '<textarea id="chat-q" placeholder="Ask anything — e.g. “Who led the league in goals in 2024-25?”" aria-label="Question"></textarea>' +
      '<button class="btn accent" id="chat-go">Ask</button>' +
      "</div>" +
      '<p class="panel-tip" style="margin-top:12px;">CPU is slow — an answer can take one to three minutes. Keep it to a single question.</p>' +
      "</div></div>";

    return {
      html,
      async bind(view) {
        const chat = view.querySelector("#chat");
        const box = view.querySelector("#chat-q");
        const go = view.querySelector("#chat-go");
        const status = view.querySelector("#ai-status");
        const add = (html, cls) => {
          const d = document.createElement("div");
          d.className = cls || "bubble bot";
          d.innerHTML = html;
          chat.appendChild(d);
          chat.scrollTop = chat.scrollHeight;
          return d;
        };

        let busy = false;
        async function ask(question) {
          if (busy || !question.trim()) return;
          busy = true;
          go.disabled = true;
          add('<span class="role">You</span>' + HI_(question), "bubble user");
          const thinking = add('<span class="role">Analyst</span><span class="dim">Reasoning…</span>');
          box.value = "";
          status.textContent = "working";
          status.classList.add("gold");
          try {
            const res = await window.HI.apiPost("/api/ai/ask", { question: question.trim() });
            thinking.outerHTML = "";
            const proof = (res.provenance || []) || [];
            add(
              '<span class="role">Analyst</span>' + (res.answer || "No answer returned."),
              "bubble bot"
            );
            if (proof.length) {
              const p = document.createElement("div");
              p.className = "provenance";
              p.innerHTML =
                "<b>Provenance</b>" +
                "<ul>" + proof.map((t) =>
                  "<li><b>" + HI_(t.tool || "?") + "</b> " +
                  (t.arguments ? smallerArgs(t.arguments) : "") +
                  " → " + HI_(trimResult(t.result)) + "</li>"
                ).join("") + "</ul>";
              chat.appendChild(p);
              chat.scrollTop = chat.scrollHeight;
            }
          } catch (err) {
            thinking.outerHTML = "";
            add("<span class='role'>Analyst</span><span style='color:var(--red-soft);'>" + HI_((err && err.message) || String(err)) + "</span>");
          }
          busy = false;
          go.disabled = false;
          status.textContent = "ready";
          status.classList.remove("gold");
        }

        try {
          const h = await window.HI.api("/api/ai/health");
          status.textContent = h.ok ? "online · " + HI_(h.configured_model || h.model || "local model") : "unavailable";
        } catch (_) {
          status.textContent = "unavailable";
        }

        add('<span class="role">Analyst</span><span class="dim">Online and ready. Ask about leaders, players, teams or seasons — I will query the database through tools and show the evidence.</span>');

        go.addEventListener("click", () => ask(box.value));
        box.addEventListener("keydown", (e) => {
          if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(box.value); }
        });
        if (q) setTimeout(() => ask(q), 300);
      },
    };
  }

  function smallerArgs(args) {
    if (!args) return "";
    try {
      const s = typeof args === "string" ? args : JSON.stringify(args);
      return '<span class="dim" style="font-size:12px;">' + HI_(s.length > 160 ? s.slice(0, 160) + "…" : s) + "</span>";
    } catch (_) { return ""; }
  }

  function trimResult(res) {
    if (res == null) return "—";
    const s = typeof res === "string" ? res : JSON.stringify(res);
    return s.length > 180 ? s.slice(0, 180) + "…" : s;
  }

  window.HI_AI = aiPage;
})();