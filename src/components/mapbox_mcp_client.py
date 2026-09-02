"""Thin JSON-RPC client for the hosted Mapbox MCP server (https://mcp.mapbox.com/mcp).

Authenticates with a Mapbox access token as a Bearer header, per Mapbox's documented
"Direct API Access" method (mapbox/mcp-server docs/hosted-mcp-guide.md, section 3.2/4).
This speaks the same JSON-RPC 2.0 tools/call protocol real MCP clients use, without the
interactive OAuth browser flow, which doesn't fit a headless Streamlit server process.
"""

import itertools
import json

import requests

from src.utils.constants import MAPBOX_ACCESS_TOKEN, MAPBOX_MCP_URL, QUERY_TIMEOUT_SECONDS
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

_id_counter = itertools.count(1)


class MapboxMCPError(Exception):
    """Raised when the Mapbox MCP server returns a JSON-RPC error or a tool-level error."""
    pass


class MapboxMCPClient:
    """Calls tools on the hosted Mapbox MCP server over JSON-RPC 2.0 / HTTP."""

    def __init__(self):
        if not MAPBOX_ACCESS_TOKEN:
            raise ValueError("MAPBOX_ACCESS_TOKEN not set in environment or secrets")
        self._headers = {
            "authorization": f"Bearer {MAPBOX_ACCESS_TOKEN}",
            "accept": "application/json, text/event-stream",
            "content-type": "application/json",
        }

    def call_tool(self, name: str, arguments: dict) -> dict:
        """Call a Mapbox MCP tool and return its `result` payload (typically containing
        `content` and, for the tools used here, `structuredContent`).
        """
        payload = {
            "jsonrpc": "2.0",
            "id": next(_id_counter),
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        try:
            response = requests.post(
                MAPBOX_MCP_URL, json=payload, headers=self._headers, timeout=QUERY_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            body = self._parse_body(response)
        except requests.RequestException as e:
            raise MapboxMCPError(f"Mapbox MCP request for '{name}' failed: {e}") from e

        if "error" in body:
            raise MapboxMCPError(f"Mapbox MCP tool '{name}' error: {body['error']}")

        result = body.get("result", {})
        if result.get("isError"):
            raise MapboxMCPError(f"Mapbox MCP tool '{name}' reported an error: {result.get('content')}")
        return result

    @staticmethod
    def _parse_body(response: requests.Response) -> dict:
        """Streamable HTTP responses may be plain JSON or an SSE stream of `data:` events."""
        content_type = response.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            for line in response.text.splitlines():
                if line.startswith("data:"):
                    return json.loads(line[len("data:"):].strip())
            raise MapboxMCPError("No data event found in Mapbox MCP SSE response")
        return response.json()
