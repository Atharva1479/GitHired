"""Local-LLM client (Ollama).

Used as a fallback when the cloud LLM (Gemini) is unavailable, or as the
primary path when ``LLM_PROVIDER=ollama``. Talks to a local Ollama
server's ``/api/chat`` endpoint.

This module is intentionally thin:
- One async function (``chat``) does the HTTP call.
- One sentinel exception (``OllamaUnavailable``) flags "we couldn't
  reach Ollama" so the caller can produce a clean reply instead of
  leaking httpx error text.
- The agent layer (``pilot_agent``) drives tool-calling on top of this,
  not this module — keeps the provider boundary clean.
"""
from __future__ import annotations

from typing import Any

import structlog

import httpx
from langsmith import traceable

from app.config import settings

log = structlog.get_logger("pilot.ollama")


class OllamaUnavailable(Exception):
    """Raised when the Ollama server can't be reached or errors out.

    Caller catches and produces a user-facing message; the exception
    str is for logs only.
    """


@traceable(name="ollama-chat", run_type="llm")
async def chat(
    messages: list[dict[str, Any]],
    *,
    tools: list[dict[str, Any]] | None = None,
    model: str | None = None,
    temperature: float = 0.4,
) -> dict[str, Any]:
    """Send a chat completion to Ollama and return the parsed JSON.

    Format follows Ollama's ``POST /api/chat`` spec:
      request:  {"model", "messages", "stream": false, "tools"?, "options"}
      response: {"message": {"role", "content", "tool_calls"?}, ...}

    Args:
        messages: Ordered list of ``{"role": "system"|"user"|"assistant"|"tool",
                  "content": "..."}`` dicts. Tool messages may also carry
                  ``"tool_call_id"`` per the OpenAI-style schema.
        tools:    Optional tool schemas. For models that don't support
                  tools, Ollama silently ignores this — the model just
                  text-answers and we fall back to that.
        model:    Override the configured default. Used in tests.
        temperature: Standard LLM temp; 0.4 keeps replies grounded
                  without sounding robotic.

    Raises:
        OllamaUnavailable: if the server is down, returns a non-2xx,
        or the response is malformed.
    """
    payload: dict[str, Any] = {
        "model": model or settings.ollama_model,
        "messages": messages,
        "stream": False,
        "keep_alive": settings.ollama_keep_alive,
        "options": {"temperature": temperature},
    }
    if tools:
        payload["tools"] = tools

    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout_seconds) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            body = r.json()
    except httpx.ConnectError as e:
        raise OllamaUnavailable(
            "Ollama server not reachable. Is it running on "
            f"{settings.ollama_base_url}? Start it with: ollama serve"
        ) from e
    except httpx.HTTPStatusError as e:
        # 404 = model not pulled. Surface that distinctly because the
        # fix is "ollama pull X" and that's worth saying out loud.
        if e.response.status_code == 404:
            raise OllamaUnavailable(
                f"Ollama model '{settings.ollama_model}' is not installed. "
                f"Pull it with: ollama pull {settings.ollama_model}"
            ) from e
        raise OllamaUnavailable(
            f"Ollama returned HTTP {e.response.status_code}"
        ) from e
    except httpx.TimeoutException as e:
        raise OllamaUnavailable(
            f"Ollama is still loading the '{settings.ollama_model}' model "
            f"into memory (timed out after {settings.ollama_timeout_seconds}s). "
            "The first request after a fresh boot is the slow one — try "
            "again in a moment and subsequent replies will be fast."
        ) from e
    except httpx.HTTPError as e:
        raise OllamaUnavailable(f"Ollama transport error: {e}") from e

    if not isinstance(body, dict) or "message" not in body:
        raise OllamaUnavailable(
            f"Ollama returned an unexpected response shape: {str(body)[:160]}"
        )
    return body


def extract_tool_calls(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the tool_calls array from an Ollama response, or [].

    Different models / Ollama versions place tool_calls in slightly
    different spots, AND return arguments in two different shapes:
      message.tool_calls = [{"function": {"name", "arguments"}}]
      message.tool_calls = [{"name", "arguments"}]
    And ``arguments`` itself can be either a dict or a JSON-encoded
    string — qwen and llama both flip-flop depending on Ollama version.
    Returns a normalised list of ``{"name", "arguments"}`` dicts with
    arguments always parsed to a dict (empty dict on parse failure).
    """
    import json as _json

    def _normalise_args(raw: Any) -> dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str) and raw.strip():
            try:
                parsed = _json.loads(raw)
                if isinstance(parsed, dict):
                    return parsed
            except _json.JSONDecodeError:
                pass
        return {}

    msg = response.get("message") or {}
    raw = msg.get("tool_calls") or []
    out: list[dict[str, Any]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        # Schema A: {"function": {"name", "arguments"}}
        fn = entry.get("function")
        if isinstance(fn, dict) and fn.get("name"):
            out.append({
                "name": fn["name"],
                "arguments": _normalise_args(fn.get("arguments")),
            })
            continue
        # Schema B: {"name", "arguments"}
        if entry.get("name"):
            out.append({
                "name": entry["name"],
                "arguments": _normalise_args(entry.get("arguments")),
            })
    return out


def extract_text(response: dict[str, Any]) -> str:
    msg = response.get("message") or {}
    return (msg.get("content") or "").strip()


async def prewarm() -> None:
    """Fire a no-op prompt at the configured model so Ollama loads its
    weights into RAM before the first real user request.

    Called from the FastAPI lifespan at startup. Crash-safe — any failure
    is logged at warning and otherwise swallowed; the app boots fine
    without Ollama (Gemini may be the only configured provider, the
    Ollama daemon may not be running, etc.).

    Uses a generous timeout (180s) because the *whole point* is to absorb
    the cold load so users don't have to. Runs in the background; the
    rest of startup does not wait for it.
    """
    if not settings.ollama_prewarm:
        return
    payload = {
        "model": settings.ollama_model,
        "messages": [{"role": "user", "content": "Reply with: ok"}],
        "stream": False,
        "keep_alive": settings.ollama_keep_alive,
        "options": {"temperature": 0.0, "num_predict": 4},
    }
    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            r = await client.post(url, json=payload)
            if r.status_code == 404:
                log.warning(
                    "ollama.prewarm.model_missing model=%s tip='ollama pull %s'",
                    settings.ollama_model, settings.ollama_model,
                )
                return
            r.raise_for_status()
            log.info(
                "ollama.prewarm.ok model=%s url=%s",
                settings.ollama_model, url,
            )
    except httpx.ConnectError:
        log.info(
            "ollama.prewarm.skipped reason=server_unreachable url=%s "
            "(this is fine if you're not using Ollama)",
            url,
        )
    except Exception as e:  # noqa: BLE001
        log.warning("ollama.prewarm.failed", error=str(e)[:200])


async def unload() -> None:
    """Unload the model from RAM immediately.

    Called on graceful backend shutdown. Sends keep_alive=0 which tells
    Ollama to evict the model as soon as this request completes.
    Crash-safe — failure is logged and swallowed.
    """
    payload = {
        "model": settings.ollama_model,
        "messages": [{"role": "user", "content": "ok"}],
        "stream": False,
        "keep_alive": 0,
        "options": {"temperature": 0.0, "num_predict": 1},
    }
    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(url, json=payload)
        log.info("ollama.unload.ok", model=settings.ollama_model)
    except Exception as e:  # noqa: BLE001
        log.warning("ollama.unload.failed", error=str(e)[:200])
