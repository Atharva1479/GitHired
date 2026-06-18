"""Unit tests for pilot_tool_adapters — TDD pass.

No real DB/Ollama/LLM needed; all external calls are mocked.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.tools import BaseTool

from app.services.pilot_tool_adapters import adapt_tools, _schema_to_pydantic_model
from app.services.pilot_tools import TOOLS, ToolContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx() -> ToolContext:
    """Return a minimal ToolContext with a fake connection (not used by unit tests)."""
    return ToolContext(user_id=42, conn=None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TestSchemaToModel
# ---------------------------------------------------------------------------


class TestSchemaToModel:
    def test_string_field_required(self) -> None:
        schema = {
            "type": "object",
            "properties": {"company": {"type": "string", "description": "Company name"}},
            "required": ["company"],
        }
        Model = _schema_to_pydantic_model("TestModel", schema)
        instance = Model(company="Acme")
        assert instance.company == "Acme"  # type: ignore[attr-defined]

    def test_optional_int_defaults_none(self) -> None:
        schema = {
            "type": "object",
            "properties": {"page": {"type": "integer", "description": "Page number"}},
        }
        Model = _schema_to_pydantic_model("TestModel", schema)
        instance = Model()
        assert instance.page is None  # type: ignore[attr-defined]

    def test_boolean_field(self) -> None:
        schema = {
            "type": "object",
            "properties": {"active": {"type": "boolean", "description": "Is active"}},
            "required": ["active"],
        }
        Model = _schema_to_pydantic_model("TestModel", schema)
        instance = Model(active=True)
        assert instance.active is True  # type: ignore[attr-defined]

    def test_array_of_string_field(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tag list",
                }
            },
            "required": ["tags"],
        }
        Model = _schema_to_pydantic_model("TestModel", schema)
        instance = Model(tags=["python"])
        assert instance.tags == ["python"]  # type: ignore[attr-defined]

    def test_empty_schema_produces_no_field_model(self) -> None:
        schema = {"type": "object", "properties": {}}
        Model = _schema_to_pydantic_model("TestModel", schema)
        instance = Model()
        assert instance is not None


# ---------------------------------------------------------------------------
# TestAdaptTools
# ---------------------------------------------------------------------------


class TestAdaptTools:
    def test_returns_list_of_base_tools(self) -> None:
        ctx = _make_ctx()
        tools = adapt_tools(ctx)
        assert len(tools) > 0
        for t in tools:
            assert isinstance(t, BaseTool)

    def test_tool_names_match_pilot_tools(self) -> None:
        ctx = _make_ctx()
        adapted_names = {t.name for t in adapt_tools(ctx)}
        pilot_names = {t.name for t in TOOLS}
        assert adapted_names == pilot_names

    @pytest.mark.asyncio
    async def test_tool_delegates_to_dispatch(self) -> None:
        ctx = _make_ctx()
        tools = adapt_tools(ctx)
        tool_map = {t.name: t for t in tools}
        list_app_tool = tool_map["list_applications"]

        mock_result: dict[str, Any] = {"count": 0, "applications": []}

        with patch(
            "app.services.pilot_tool_adapters.dispatch",
            new=AsyncMock(return_value=mock_result),
        ) as mock_dispatch:
            await list_app_tool.ainvoke({"status": "applied"})
            # Verify dispatch was called with correct tool name and includes
            # the provided status field (Pydantic fills other optional fields
            # as None).
            assert mock_dispatch.call_count == 1
            call_args = mock_dispatch.call_args[0]
            assert call_args[0] == "list_applications"
            assert call_args[1]["status"] == "applied"
            assert call_args[2] == ctx

    @pytest.mark.asyncio
    async def test_none_valued_optional_field_forwarded_to_dispatch(self) -> None:
        """Pydantic None defaults for optional fields must reach dispatch."""
        ctx = _make_ctx()

        captured_args: dict[str, Any] = {}

        async def _capture(name: str, args: dict[str, Any], ctx: Any) -> dict[str, Any]:
            captured_args.update(args)
            return {}

        with patch(
            "app.services.pilot_tool_adapters.dispatch", side_effect=_capture
        ):
            tools = adapt_tools(ctx)
            list_apps = next(t for t in tools if t.name == "list_applications")
            # Invoke without "status" — Pydantic fills it as None
            await list_apps.ainvoke({})

        # After the fix: "status" key is present (as None) in dispatch kwargs
        assert "status" in captured_args
        assert captured_args["status"] is None
