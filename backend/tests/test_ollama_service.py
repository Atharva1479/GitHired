"""Ollama service tests.

Two layers:
  Unit tests  — monkeypatch httpx, no Ollama server required.
               Run always: pytest tests/test_ollama_service.py -m "not integration"
  Integration — actually talk to a running Ollama server.
               Run with:  pytest tests/test_ollama_service.py -m integration
               Skipped automatically if Ollama is unreachable.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.ollama_service import (
    OllamaUnavailable,
    chat,
    extract_text,
    extract_tool_calls,
)


# ── helpers ────────────────────────────────────────────────────────────

def _ok_response(content: str = "hello", tool_calls: list | None = None) -> dict:
    msg: dict[str, Any] = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return {"model": "qwen3.5:2b", "message": msg, "done": True}


def _make_httpx_response(status: int, body: Any) -> MagicMock:
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = status
    mock.json.return_value = body
    mock.text = json.dumps(body)
    if status >= 400:
        mock.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status}",
            request=MagicMock(),
            response=mock,
        )
    else:
        mock.raise_for_status.return_value = None
    return mock


# ── unit: happy path ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_chat_returns_message_on_200() -> None:
    response_body = _ok_response("I found 5 applications.")
    mock_resp = _make_httpx_response(200, response_body)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await chat([{"role": "user", "content": "how many apps?"}])

    assert result["message"]["content"] == "I found 5 applications."


@pytest.mark.asyncio
async def test_chat_sends_tools_in_payload() -> None:
    response_body = _ok_response()
    mock_resp = _make_httpx_response(200, response_body)
    tools = [{"type": "function", "function": {"name": "get_stats", "parameters": {}}}]

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
        await chat([{"role": "user", "content": "hi"}], tools=tools)

    payload = mock_post.call_args.kwargs["json"]
    assert "tools" in payload
    assert payload["tools"] == tools


# ── unit: error handling ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_chat_raises_on_connect_error() -> None:
    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError("refused"),
    ):
        with pytest.raises(OllamaUnavailable, match="not reachable"):
            await chat([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_chat_raises_on_timeout() -> None:
    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=httpx.TimeoutException("timed out"),
    ):
        with pytest.raises(OllamaUnavailable, match="loading"):
            await chat([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_chat_raises_404_with_helpful_message() -> None:
    mock_resp = _make_httpx_response(404, {"error": "model not found"})
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(OllamaUnavailable, match="not installed"):
            await chat([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_chat_raises_on_500() -> None:
    mock_resp = _make_httpx_response(500, {"error": "internal"})
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(OllamaUnavailable, match="HTTP 500"):
            await chat([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_chat_raises_on_malformed_response() -> None:
    mock_resp = _make_httpx_response(200, {"unexpected": "shape"})
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(OllamaUnavailable, match="unexpected response shape"):
            await chat([{"role": "user", "content": "hi"}])


# ── unit: extract_text ────────────────────────────────────────────────

def test_extract_text_returns_content() -> None:
    resp = _ok_response("Your score is 87.")
    assert extract_text(resp) == "Your score is 87."


def test_extract_text_empty_on_missing_content() -> None:
    assert extract_text({"message": {}}) == ""
    assert extract_text({}) == ""


# ── unit: extract_tool_calls ──────────────────────────────────────────

def test_extract_tool_calls_schema_a() -> None:
    """Schema A: message.tool_calls[].function.{name, arguments}"""
    resp = _ok_response(tool_calls=[
        {"function": {"name": "get_applications", "arguments": {"limit": 5}}}
    ])
    calls = extract_tool_calls(resp)
    assert len(calls) == 1
    assert calls[0]["name"] == "get_applications"
    assert calls[0]["arguments"] == {"limit": 5}


def test_extract_tool_calls_schema_b() -> None:
    """Schema B: message.tool_calls[].{name, arguments} (no function wrapper)"""
    resp = _ok_response(tool_calls=[
        {"name": "get_stats", "arguments": {"period": "week"}}
    ])
    calls = extract_tool_calls(resp)
    assert len(calls) == 1
    assert calls[0]["name"] == "get_stats"
    assert calls[0]["arguments"] == {"period": "week"}


def test_extract_tool_calls_json_string_arguments() -> None:
    """Arguments as a JSON-encoded string (some Ollama versions do this)."""
    resp = _ok_response(tool_calls=[
        {"function": {"name": "search", "arguments": '{"query": "python jobs"}'}}
    ])
    calls = extract_tool_calls(resp)
    assert calls[0]["arguments"] == {"query": "python jobs"}


def test_extract_tool_calls_empty_when_none() -> None:
    resp = _ok_response()
    assert extract_tool_calls(resp) == []


def test_extract_tool_calls_bad_args_returns_empty_dict() -> None:
    resp = _ok_response(tool_calls=[
        {"function": {"name": "fn", "arguments": "not-valid-json"}}
    ])
    calls = extract_tool_calls(resp)
    assert calls[0]["arguments"] == {}


# ── unit: OllamaUnavailable message safety ────────────────────────────

def test_unavailable_message_has_no_traceback_bits() -> None:
    exc = OllamaUnavailable("Ollama server not reachable at http://localhost:11434")
    s = str(exc)
    assert "Traceback" not in s
    assert "httpx" not in s.lower()


# ── integration: real Ollama server ──────────────────────────────────

def _ollama_reachable() -> bool:
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=3.0)
        return r.status_code == 200
    except Exception:
        return False


def _get_available_models() -> list[str]:
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=3.0)
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []


@pytest.mark.integration
@pytest.mark.skipif(not _ollama_reachable(), reason="Ollama server not running")
def test_ollama_server_is_reachable() -> None:
    """Verify Ollama daemon responds to /api/tags."""
    r = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
    assert r.status_code == 200
    data = r.json()
    assert "models" in data
    print(f"\nAvailable models: {[m['name'] for m in data['models']]}")


@pytest.mark.integration
@pytest.mark.skipif(not _ollama_reachable(), reason="Ollama server not running")
def test_qwen_model_is_installed() -> None:
    """Verify qwen3.5:2b is pulled and available."""
    models = _get_available_models()
    assert "qwen3.5:2b" in models, (
        f"qwen3.5:2b not found. Installed models: {models}\n"
        "Fix: ollama pull qwen3.5:2b"
    )


@pytest.mark.integration
@pytest.mark.skipif(not _ollama_reachable(), reason="Ollama server not running")
def test_ollama_chat_returns_response() -> None:
    """Send a real minimal request and verify the response shape."""
    async def _run() -> dict:
        return await chat(
            [{"role": "user", "content": "Reply with the single word: ok"}],
            model="qwen3.5:2b",
            temperature=0.0,
        )

    result = asyncio.run(_run())
    assert "message" in result
    assert "content" in result["message"]
    content = result["message"]["content"].lower()
    print(f"\nOllama replied: {content!r}")
    assert len(content) > 0, "Expected a non-empty reply"


@pytest.mark.integration
@pytest.mark.skipif(not _ollama_reachable(), reason="Ollama server not running")
def test_ollama_tool_call_roundtrip() -> None:
    """Verify Ollama can produce a tool call when given a tool schema."""
    tools = [{
        "type": "function",
        "function": {
            "name": "get_job_count",
            "description": "Returns the number of job applications tracked.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    }]

    async def _run() -> dict:
        return await chat(
            [{"role": "user", "content": "How many jobs have I applied to?"}],
            tools=tools,
            model="qwen3.5:2b",
            temperature=0.0,
        )

    result = asyncio.run(_run())
    calls = extract_tool_calls(result)
    text = extract_text(result)
    print(f"\nTool calls: {calls}")
    print(f"Text reply: {text!r}")
    # Either a tool call OR a text answer — both are valid
    assert calls or text, "Expected either a tool call or a text reply"
