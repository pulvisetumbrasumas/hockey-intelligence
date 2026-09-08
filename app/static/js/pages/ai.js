/* ============================================================
   AI HOCKEY ANALYST — local, database-grounded chat
   ============================================================ */
(function () {
  "use strict";
  const HI_ = window.HI.escape;

  async function aiPage(ctx) {
    const q = (ctx.query && ctx.query.q) || "";
    const html =
      '<div class="section" style="margin-top:24px;">' +
      '<div class="head">' +
      "<div><span class='eyebrow'>Local reasoning</span>" +
      '<h1 class="page-title" style="margin:2px 0 4px;">AI Hockey Analyst</h1></div>' +
      '<span class="pill-tag cyan" id="ai-status">checking</span></div>' +
      '<p class="page-sub">Ollama runs entirely on this machine. It plans a query, resolves verified facts from the database through tools, then explains what the data shows — and streams the answer as it is generated. It cannot invent numbers; every figure is traceable in the panel.</p>' +
      '<div class="card">' +
      '<div class="chat" id="chat"></div>' +
      '<div class="chat-input">' +
      '<textarea id="chat-q" placeholder="Ask anything — e.g. “Who led the league in goals in 2024-25?”" aria-label="Question"></textarea>' +
      '<button class="btn accent" id="chat-go">Ask</button>' +
      "</div>" +
      '<p class="panel-tip" style="margin-top:12px;">CPU is slow, so keep it to a single question — but the answer now streams in as the model finishes paragraphs.</p>' +
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
          const bot = add('<span class="role">Analyst</span><span class="dim" id="ai-typing">Connecting…</span>');
          box.value = "";
          status.textContent = "working";
          status.classList.add("gold");
          let prose = "";
          const showTool = (ev) => {
            const chip = document.createElement("div");
            chip.className = "ai-tool";
            chip.textContent = "tool: " + HI_(ev.name || "?") + (ev.status === "error" ? " (error)" : "");
            bot.appendChild(chip);
            chat.scrollTop = chat.scrollHeight;
          };
          let lastStatus = null;
          const showStatus = (ev) => {
            if (ev.text === lastStatus) return;
            lastStatus = ev.text;
            const note = document.createElement("div");
            note.className = "dim";
            note.style.fontSize = "12px";
            note.style.marginTop = "4px";
            note.textContent = "… " + ev.text;
            bot.appendChild(note);
            chat.scrollTop = chat.scrollHeight;
          };
          const showProvenance = (proof) => {
            if (!proof || !proof.length) return;
            const p = document.createElement("div");
            p.className = "provenance";
            p.innerHTML =
              "<b>Provenance</b>" +
              "<ul>" + proof.map((t) =>
                "<li><b>" + HI_(t.tool || "?") + "</b> " +
                (t.arguments ? smallerArgs(t.arguments) : "") +
                " → " + HI_(trimResult(t.result)) + "</li>"
              ).join("") + "</ul>";
            bot.appendChild(p);
            chat.scrollTop = chat.scrollHeight;
          };
          const fallback = async () => {
            const res = await window.HI.apiPost("/api/ai/ask", { question: question.trim() });
            bot.innerHTML = '<span class="role">Analyst</span>' + (res.answer || "No answer returned.");
            showProvenance(res.provenance || []);
          };
          try {
            bot.innerHTML = '<span class="role">Analyst</span><span></span>';
            const out = bot.querySelector("span:last-child");
            const resp = await fetch("/api/ai/ask/stream", {
              method: "POST",
              headers: window.HI.authHeaders({ "Content-Type": "application/json" }),
              body: JSON.stringify({ question: question.trim() }),
            });
            if (!resp.ok || !resp.body) throw new Error(resp.statusText || "stream failed");
            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            let buf = "";
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;
              buf += decoder.decode(value, { stream: true });
              const parts = buf.split("\n\n");
              buf = parts.pop() || "";
              for (const part of parts) {
                const line = part.trim();
                if (!line.startsWith("data:")) continue;
                let ev;
                try { ev = JSON.parse(line.slice(5).trim()); } catch (_) { continue; }
                if (ev.type === "delta") { prose += ev.text; out.textContent = prose; }
                else if (ev.type === "tool") { showTool(ev); }
                else if (ev.type === "status") { showStatus(ev); }
                else if (ev.type === "done") { showProvenance(ev.provenance || []); }
                else if (ev.type === "error") { out.textContent = "Error: " + HI_(ev.message || "unknown"); }
              }
              chat.scrollTop = chat.scrollHeight;
            }
            if (!prose.trim()) await fallback();
          } catch (err) {
            bot.innerHTML = '<span class="role">Analyst</span><span class="dim">Stream unavailable, trying direct chat…</span>';
            try { await fallback(); } catch (err2) {
              bot.innerHTML = '<span class="role">Analyst</span><span style="color:var(--red-soft);">' + HI_((err2 && err2.message) || String(err2)) + "</span>";
            }
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