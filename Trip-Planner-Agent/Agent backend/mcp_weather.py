"""
mcp_weather.py
==============
MCP demo: a weather "server" and "client" living in the same process.

Why in-process? It keeps the instrumentation example self-contained - you can
see MCP spans in Arize without deploying a separate server. The LangChain tool
`mcp_weather` is the only thing the agents see.
"""

from __future__ import annotations

from typing import Optional

from langchain_core.tools import tool

from config import ENABLE_MCP


class MCPWeatherClient:
    """In-process MCP server + client pair for deterministic weather lookups.

    The server is a `FastMCP` instance; `lookup()` spins up a connected client
    session, calls the tool, and returns the text content.
    """

    def __init__(self) -> None:
        # Imported lazily so the module is importable when MCP is disabled.
        import anyio
        from mcp.server import FastMCP
        from mcp.shared.memory import create_connected_server_and_client_session

        self._anyio = anyio
        self._create_session = create_connected_server_and_client_session
        self._tool_name = "weather_mcp"

        # Static dataset keeps the demo deterministic (and offline-friendly).
        self._weather_db = {
            "prague": {
                "temperature": "6-14°C",
                "conditions": "Crisp mornings, light rain",
                "advice": "Layer up and carry a compact umbrella",
            },
            "bangkok": {
                "temperature": "27-33°C",
                "conditions": "Humid afternoons, evening storms",
                "advice": "Light fabrics, hydrate, bring a poncho",
            },
            "dubai": {
                "temperature": "24-36°C",
                "conditions": "Dry heat with breezy nights",
                "advice": "High-SPF sunscreen and breathable layers",
            },
            "barcelona": {
                "temperature": "14-24°C",
                "conditions": "Sunny with a coastal breeze",
                "advice": "Light jacket for evenings, sunscreen by day",
            },
            "tokyo": {
                "temperature": "10-22°C",
                "conditions": "Cool mornings, clear afternoons",
                "advice": "Layered outfits and comfortable rainproof shoes",
            },
            "rome": {
                "temperature": "12-23°C",
                "conditions": "Mild with scattered showers",
                "advice": "Carry a light sweater and umbrella",
            },
            "lisbon": {
                "temperature": "13-21°C",
                "conditions": "Coastal breeze, patchy clouds",
                "advice": "Windbreaker plus comfy walking shoes",
            },
            "marrakech": {
                "temperature": "16-30°C",
                "conditions": "Warm days, cool desert nights",
                "advice": "Layer your outfits and pack sun protection",
            },
            "new york": {
                "temperature": "5-18°C",
                "conditions": "Variable with a chance of rain",
                "advice": "Light coat, closed shoes, compact umbrella",
            },
        }

        self._server = FastMCP(
            name="Weather MCP Demo",
            instructions="Deterministic weather tool for instrumentation demos.",
        )

        # Register the MCP tool - let MCP instrumentation handle tracing.
        @self._server.tool(
            name=self._tool_name,
            description="Return a simple weather briefing for a destination.",
        )
        def _weather_tool(destination: str) -> str:
            return self._build_summary(destination)

    # -- public API ---------------------------------------------------------
    def lookup(self, destination: str) -> str:
        """Synchronous wrapper around the async MCP call."""
        return self._anyio.run(self._invoke_tool, destination)

    # -- internals ----------------------------------------------------------
    async def _invoke_tool(self, destination: str) -> str:
        async with self._create_session(
            self._server._mcp_server,
            raise_exceptions=True,
        ) as session:
            # list_tools() populates metadata needed for validation + traces.
            await session.list_tools()
            result = await session.call_tool(self._tool_name, {"destination": destination})
            if result.isError:
                raise RuntimeError("MCP weather tool returned an error result")

            parts = []
            for block in result.content:
                text_val = getattr(block, "text", None)
                if text_val:
                    parts.append(text_val)

            summary = "\n".join(parts).strip()
            if not summary:
                raise RuntimeError("MCP weather tool produced no content")
            return summary

    def _build_summary(self, destination: str) -> str:
        """Format the canned weather row for `destination`."""
        city_key = destination.split(",")[0].strip().lower()
        payload = self._weather_db.get(city_key)
        if payload:
            return (
                f"MCP Weather • {destination}: {payload['temperature']} with "
                f"{payload['conditions']}. Tip: {payload['advice']}."
            )
        return (
            f"MCP Weather • {destination}: Seasonal averages unavailable. "
            "Check a forecast a few days ahead and pack adaptable layers."
        )


# ---------------------------------------------------------------------------
# Singleton client - only instantiated when the feature flag allows it.
# ---------------------------------------------------------------------------
MCP_WEATHER_CLIENT: Optional[MCPWeatherClient] = None
if ENABLE_MCP:
    MCP_WEATHER_CLIENT = MCPWeatherClient()


@tool
def mcp_weather(destination: str) -> str:
    """Get current weather conditions and packing advice for the destination via MCP."""
    if MCP_WEATHER_CLIENT:
        return MCP_WEATHER_CLIENT.lookup(destination)
    raise RuntimeError("MCP weather client failed to initialize.")