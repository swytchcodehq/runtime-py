"""Vercel AI SDK provider (Python equivalent)."""
from __future__ import annotations
import asyncio
from .base import Provider, Tool

class VercelProvider(Provider):
    def format_tool(self, tool: Tool):
        try:
            from ai_sdk import tool as vercel_tool
        except ImportError:
            raise ImportError("Please install the Vercel AI SDK (requires Python 3.12+): pip install ai-sdk-python")

        # Verified against ai_sdk.tool.Tool.run: the SDK invokes the handler as
        # `handler(**kwargs)` (arguments by field name, never a positional dict)
        # and awaits the result if it is awaitable. So an async handler taking
        # **kwargs matches exactly; using **kwargs (not a positional param) also
        # avoids colliding with a tool field literally named "args". We offload
        # the blocking CLI call to a thread so the awaited handler never stalls
        # the event loop.
        async def _execute(**kwargs):
            return await asyncio.to_thread(tool.execute, kwargs)

        return vercel_tool(
            name=tool.name,
            description=tool.description,
            parameters=tool.input_schema,
            execute=_execute,
        )
