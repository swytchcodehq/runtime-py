"""Provider base (Composio-style Agentic / NonAgentic split)."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable

@dataclass
class Tool:
    canonical_id: str
    name: str
    description: str
    input_schema: dict
    execute: Callable[[dict], Any]

class Provider:
    def format_tool(self, tool: Tool) -> Any:
        raise NotImplementedError
        
    def format_tools(self, tools: list[Tool]) -> list[Any]:
        return [self.format_tool(t) for t in tools]
