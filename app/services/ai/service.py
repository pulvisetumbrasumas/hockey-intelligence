from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.ai.tools import ToolResults, build_tool_schemas

logger = logging.getLogger(__name__)


def _coerce(value: Any) -> Any:
    """Recursively parse JSON-string argument values (e.g. "[1, 2]" -> [1, 2]).

    Small models frequently emit nested arguments as JSON strings instead of
    real arrays/objects. Coerce them so the deterministic tool layer receives
    usable values.
    """
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith(("[", "{")):
            try:
                return _coerce(json.loads(stripped))
            except json.JSONDecodeError:
                return value
        try:
            return int(stripped)
        except (ValueError, TypeError):
            return value
    if isinstance(value, list):
        return [_coerce(v) for v in value]
    if isinstance(value, dict):
        return {k: _coerce(v) for k, v in value.items()}
    return value

SYSTEM_PROMPT = (
    "You are the Hockey Intelligence reasoning layer, part of an open-source "
    "NHL application.\n"
    "\n"
    "CORE PRINCIPLES\n"
    "1. The database is the source of truth. The statistics engine computes all "
    "numbers deterministically.\n"
    "2. You must NEVER invent statistics, players, games, trades, awards, "
    "contracts, records, or historical events.\n"
    "3. When you need data, call the available tools. Use the verified tool "
    "results in your answer - never rely on your internal memory for numbers.\n"
    "4. NEVER guess or fabricate numeric player or team IDs. NHL IDs are 7-8 "
    "digit numbers you do not know. Instead, pass a player's full name to the "
    "tools that accept one (e.g. \"full_name\": \"Connor McDavid\"), or call "
    "search_players first to obtain a real ID from the database. If a lookup "
    "returns an error, do not invent the data.\n"
    "5. If the required information does not exist in the database, say so "
    "clearly rather than guessing.\n"
    "6. For questions about who led the league in a category (season or "
    "all-time), use get_league_leaders with the correct stat name (points, "
    "goals, assists, save_pct, wins, etc.) instead of guessing a winner.\n"
    "\n"
    "DISTINGUISHING KNOWLEDGE\n"
    "Always separate:\n"
    "- WHAT HAPPENED (facts the database establishes)\n"
    "- WHAT THE DATA SHOWS (what the statistics imply)\n"
    "- WHAT CAN REASONABLY BE INFERRED (reasonable interpretation, clearly "
    "labeled)\n"
    "- WHAT REQUIRES CONTEXT OR HUMAN JUDGMENT (do not present interpretation "
    "as fact)\n"
    "\n"
    "COMPARISONS\n"
    "When comparing players, do NOT declare a single winner based on one "
    "statistic. Report evidence per dimension. Say things like:\n"
    '- "Player A is stronger statistically in X."\n'
    '- "Player B has stronger evidence in Y."\n'
    '- "The available data does not establish a meaningful difference in Z."\n'
    '- "The answer depends on what definition of greatness is being used."\n'
    "Never reduce hockey to a single number.\n"
    "\n"
    "HISTORICAL AWARENESS\n"
    "Rules, schedules, league size, equipment, and scoring environments changed "
    "over time.\n"
    "Do not judge historical players exclusively using modern statistics.\n"
    "Preserve historical franchises: Hartford Whalers are not the Carolina "
    "Hurricanes in identity, though they share a franchise lineage.\n"
    "\n"
    "ANSWER STYLE\n"
    "Answer naturally like a knowledgeable hockey person. Be direct. Use the "
    "actual numbers from tool results.\n"
    "Admit uncertainty when data is insufficient.\n"
    "If you used tools, reference the facts they returned. If data could not "
    "be found, say so."
)


class OllamaAIService:
    """AI reasoning layer backed by Ollama.

    The model, endpoint, context size, and generation parameters are all
    configurable via configuration/environment variables, so the underlying
    model can be swapped without restructuring the application.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.ollama_base_url.rstrip("/")
        self.model = self.settings.ollama_model
        self.timeout = self.settings.ollama_timeout

    def _default_options(self) -> dict[str, Any]:
        return {
            "temperature": self.settings.ollama_temperature,
            "num_ctx": self.settings.ollama_num_ctx,
        }

    async def _chat(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": self._default_options(),
            "keep_alive": self.settings.ollama_keep_alive,
        }
        if tools:
            payload["tools"] = tools
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def ask(
        self, question: str, session: AsyncSession | None = None
    ) -> dict[str, Any]:
        """Answer a natural-language hockey question using database-grounded tools.

        Executes the Ollama tool-calling loop. When a session is provided, tool
        calls are resolved against the database and the verified results are
        fed back into the conversation so the model never guesses numbers.
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        tool_schemas = build_tool_schemas()
        tool_calls_used: list[dict[str, Any]] = []
        provenance: list[dict[str, Any]] = []
        resolver = ToolResults(session) if session is not None else None

        for _ in range(8):
            response = await self._chat(messages, tool_schemas)
            msg = response.get("message", {})
            content = msg.get("content") or ""
            calls = msg.get("tool_calls") or []
            if not calls:
                return {
                    "answer": content,
                    "model": response.get("model", self.model),
                    "tool_calls": tool_calls_used,
                    "provenance": provenance,
                }
            messages.append(
                {"role": "assistant", "content": content or "", "tool_calls": calls}
            )
            for call in calls:
                fn = call.get("function", {})
                name = fn.get("name", "")
                raw_args = fn.get("arguments", "{}")
                if isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args)
                    except json.JSONDecodeError:
                        args = {}
                else:
                    args = raw_args or {}
                args = {k: _coerce(v) for k, v in args.items()}

                if resolver is not None:
                    outcome = await resolver._execute(name, args)
                    result_text = json.dumps(outcome, default=str)
                    provenance.append({"tool": name, "arguments": args, "result": outcome})
                else:
                    result_text = json.dumps(
                        {"error": "Database session unavailable."}, default=str
                    )
                tool_calls_used.append({"name": name, "arguments": args})
                messages.append(
                    {"role": "tool", "content": result_text}
                )

        return {
            "answer": (
                "I attempted multiple tool calls but did not reach a final answer. "
                "Please try rephrasing the question."
            ),
            "model": self.model,
            "tool_calls": tool_calls_used,
            "provenance": provenance,
            "truncated": True,
        }

    async def ask_with_session(
        self, question: str, session: AsyncSession
    ) -> dict[str, Any]:
        return await self.ask(question, session)

    async def _stream_chat(
        self,
        client: httpx.AsyncClient,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream one Ollama /api/chat turn, yielding delta/done events.

        Ollama emits NDJSON lines; tool_calls can arrive in their own line(s),
        so they are accumulated until the `done` flag.
        """
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": self._default_options(),
            "keep_alive": self.settings.ollama_keep_alive,
        }
        if tools:
            payload["tools"] = tools
        async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
            resp.raise_for_status()
            buffer = ""
            message: dict[str, Any] = {}
            tool_calls: list[dict[str, Any]] = []
            model = self.model
            idle_seq = iter(
                ("Still planning — the local CPU is chewing on the reply…",
                 "Still working — the reply is being written token by token…",
                 "Still generating — this model runs everything on this machine…")
            )
            idle_wait_s = 12
            lines = resp.aiter_lines()
            while True:
                try:
                    line = await asyncio.wait_for(lines.__anext__(), timeout=idle_wait_s)
                except TimeoutError:
                    yield {"type": "status", "text": next(idle_seq, "Still generating…")}
                    continue
                except StopAsyncIteration:
                    break
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                m = data.get("message", {})
                content = m.get("content") or ""
                if content:
                    delta = content[len(buffer):] if content.startswith(buffer) else content
                    if delta:
                        yield {"type": "delta", "text": delta}
                    buffer = content
                calls = m.get("tool_calls") or []
                if calls:
                    tool_calls.extend(calls)
                if data.get("done"):
                    message = m
                    model = data.get("model", model)
                if not message and content:
                    message = {"role": "assistant", "content": buffer}
            yield {
                "type": "done",
                "message": message or {"role": "assistant", "content": buffer},
                "model": model,
                "tool_calls": tool_calls,
            }

    async def ask_stream(
        self, question: str, session: AsyncSession | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream an answer to a natural-language hockey question.

        Yields events as they happen: {"type":"delta","text":...} answer tokens,
        {"type":"tool",...} when a tool is resolved, and a final {"type":"done",...}.
        The tool loop runs inside a single stream, so callers render live updates
        instead of waiting for the complete round-trip.
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        tool_schemas = build_tool_schemas()
        tool_calls_used: list[dict[str, Any]] = []
        provenance: list[dict[str, Any]] = []
        resolver = ToolResults(session) if session is not None else None

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for _ in range(8):
                content = ""
                calls: list[dict[str, Any]] = []
                model = self.model
                async for ev in self._stream_chat(client, messages, tool_schemas):
                    if ev["type"] == "delta":
                        content += ev["text"]
                        yield ev
                    elif ev["type"] == "done":
                        model = ev["model"]
                        content = ev["message"].get("content") or content
                        calls = ev["tool_calls"] or []

                if not calls:
                    yield {
                        "type": "done",
                        "model": model,
                        "tool_calls": tool_calls_used,
                        "provenance": provenance,
                    }
                    return

                messages.append(
                    {"role": "assistant", "content": content or "", "tool_calls": calls}
                )
                for call in calls:
                    fn = call.get("function", {})
                    name = fn.get("name", "")
                    raw_args = fn.get("arguments", "{}")
                    if isinstance(raw_args, str):
                        try:
                            args = json.loads(raw_args)
                        except json.JSONDecodeError:
                            args = {}
                    else:
                        args = raw_args or {}
                    args = {k: _coerce(v) for k, v in args.items()}
                    tool_calls_used.append({"name": name, "arguments": args})
                    status = "ok"
                    try:
                        if resolver is not None:
                            outcome = await resolver._execute(name, args)
                            provenance.append({"tool": name, "arguments": args, "result": outcome})
                        else:
                            outcome = {"error": "Database session unavailable."}
                    except Exception as exc:  # keep the loop alive on tool failures
                        logger.warning("Tool %s failed: %s", name, exc)
                        outcome = {"error": str(exc)}
                        status = "error"
                    messages.append(
                        {"role": "tool", "content": json.dumps(outcome, default=str)}
                    )
                    yield {"type": "tool", "name": name, "arguments": args, "status": status}

        yield {
            "type": "done",
            "truncated": True,
            "model": self.model,
            "tool_calls": tool_calls_used,
            "provenance": provenance,
        }

    async def health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                models = [m.get("name") for m in data.get("models", [])]
                return {
                    "ok": True,
                    "endpoint": self.base_url,
                    "configured_model": self.model,
                    "available_models": models,
                }
        except httpx.HTTPError as exc:
            return {"ok": False, "endpoint": self.base_url, "error": str(exc)}
