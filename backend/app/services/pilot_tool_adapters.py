"""Thin adapter layer: converts pilot_tools.TOOLS into LangChain StructuredTool objects.

This module is part of the LangGraph migration for the Pilot AI voice agent.
pilot_tools.py and pilot.py are read-only contracts — this module must not modify them.
"""
from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, create_model
from pydantic.fields import FieldInfo

from app.services.pilot_tools import TOOLS, ToolContext, dispatch

# ---------------------------------------------------------------------------
# JSON-Schema → Pydantic model
# ---------------------------------------------------------------------------

_TYPE_MAP: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
}


def _schema_to_pydantic_model(model_name: str, schema: dict[str, Any]) -> type[BaseModel]:
    """Convert a JSON Schema object definition to a Pydantic v2 BaseModel.

    Supported types: string, integer, number, boolean, array (with items.type).
    Unknown types fall back to Any.
    Required fields get no default; optional fields default to None.
    """
    properties: dict[str, Any] = schema.get("properties") or {}
    required: list[str] = schema.get("required") or []

    field_definitions: dict[str, Any] = {}
    for field_name, field_schema in properties.items():
        raw_type = field_schema.get("type", "")
        description: str = field_schema.get("description", "")

        if raw_type == "array":
            items_type_str = (field_schema.get("items") or {}).get("type", "")
            item_py_type = _TYPE_MAP.get(items_type_str, Any)
            python_type: Any = list[item_py_type]  # type: ignore[valid-type]
        else:
            python_type = _TYPE_MAP.get(raw_type, Any)

        if field_name in required:
            field_definitions[field_name] = (python_type, FieldInfo(description=description))
        else:
            field_definitions[field_name] = (
                python_type | None,
                FieldInfo(default=None, description=description),
            )

    return create_model(model_name, **field_definitions)  # type: ignore[call-overload]


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


def adapt_tools(ctx: ToolContext) -> list[StructuredTool]:
    """Return a LangChain StructuredTool for every tool in TOOLS, bound to ctx."""
    adapted: list[StructuredTool] = []

    for tool in TOOLS:
        args_schema = _schema_to_pydantic_model(
            f"_{tool.name}_args",
            tool.parameters,
        )

        # Capture tool.name per iteration with a default argument to avoid
        # late-binding closure issues.
        # Each invocation acquires its own connection from the pool so that
        # LangGraph's parallel tool dispatch never hits asyncpg's
        # "another operation is in progress" error on a shared connection.
        async def _coroutine(
            _tool_name: str = tool.name, **kwargs: Any
        ) -> str:
            if ctx.pool is not None:
                async with ctx.pool.acquire() as tool_conn:
                    fresh_ctx = ToolContext(user_id=ctx.user_id, conn=tool_conn, pool=ctx.pool)
                    result = await dispatch(_tool_name, kwargs, fresh_ctx)
            else:
                result = await dispatch(_tool_name, kwargs, ctx)
            return json.dumps(result, default=str)

        structured = StructuredTool.from_function(
            name=tool.name,
            description=tool.description,
            args_schema=args_schema,
            coroutine=_coroutine,
        )
        adapted.append(structured)

    return adapted
