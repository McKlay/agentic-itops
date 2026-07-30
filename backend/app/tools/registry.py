from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Central registry for all agent tools.

    Tools are registered with a name, an async handler, and an OpenAI
    function-call schema.  Agents call ``get_schemas(tool_names)`` to obtain
    the schema list to pass to ``chat_completion(tools=...)``, and call
    ``execute(name, arguments)`` to dispatch a tool call returned by the LLM.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, Callable] = {}
        self._schemas: dict[str, dict[str, Any]] = {}

    def register(self, name: str, handler: Callable, schema: dict[str, Any]) -> None:
        """Register a tool handler and its OpenAI function-call schema.

        ``handler`` must be an async callable whose keyword arguments match the
        ``parameters.properties`` keys defined in ``schema``.
        """
        self._handlers[name] = handler
        self._schemas[name] = schema
        logger.debug("ToolRegistry: registered tool '%s'", name)

    def get_schemas(self, tool_names: list[str]) -> list[dict[str, Any]]:
        """Return the OpenAI function-call schema dicts for the requested tools.

        Unknown tool names are silently skipped so agents can declare a superset
        and the registry only returns what has actually been registered.
        """
        return [self._schemas[n] for n in tool_names if n in self._schemas]

    async def execute(self, name: str, arguments: dict[str, Any]) -> Any:
        """Dispatch a tool call by name with the given arguments dict.

        Raises ``KeyError`` if *name* is not registered.
        """
        if name not in self._handlers:
            raise KeyError(f"Tool '{name}' is not registered in ToolRegistry.")
        logger.debug("ToolRegistry: executing '%s' with args=%s", name, arguments)
        return await self._handlers[name](**arguments)
