"""MCP server for the ECHO AI Lab Streamlit apps: catalogue, health, wake, screenshot and browse.

Run it directly (stdio):  python mcp/server.py
Register with Claude Code: claude mcp add echo-apps -s user -- <python> <abs path>/mcp/server.py

All the work happens in core.py, which has no MCP dependency; this file only exposes it as tools.
Needs a reasonably recent SDK: mcp 1.27 with pydantic 2.7 fails to build a tool schema for a
plain-string return ("A non-annotated attribute was detected: result").
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core  # noqa: E402

from mcp.server.fastmcp import FastMCP  # noqa: E402

try:  # lets screenshots come back as an image the model can see
    from mcp.server.fastmcp import Image
except ImportError:  # pragma: no cover - older SDKs
    Image = None

# stdio carries the MCP protocol: keep chatty client logs out of it
for noisy in ("httpx", "httpcore", "urllib3"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

mcp = FastMCP("echo-apps")


@mcp.tool()
async def list_apps(pillar: str = "", category: str = "", query: str = "",
                    deployed_only: bool = False, limit: int = 40) -> str:
    """List the lab's applications from the portfolio catalogue.

    pillar/category filter exactly (case-insensitive); query matches title, description or stack.
    deployed_only keeps apps with a known Streamlit Cloud URL (run discover_apps first).
    """
    return await core.list_apps(pillar, category, query, deployed_only, limit)


@mcp.tool()
async def get_app(name: str) -> dict:
    """Full catalogue entry for one application, plus its Streamlit Cloud URL if known."""
    return await core.get_app(name)


@mcp.tool()
async def check_app(name_or_url: str, deep: bool = True) -> dict:
    """Is the app up, asleep, private or missing?

    HTTP alone only proves the URL exists (404 = no such app); a sleeping or private app still
    answers 200, so deep=True (default) opens it in a headless browser to read the real state.
    """
    return await core.check_app(name_or_url, deep)


@mcp.tool()
async def wake_app(name_or_url: str, timeout_s: int = 150) -> dict:
    """Wake a sleeping Streamlit Cloud app by clicking 'Yes, get this app back up!' and wait for it."""
    return await core.wake_app(name_or_url, timeout_s)


@mcp.tool()
async def screenshot_app(name_or_url: str, width: int = 1440, height: int = 900, wait_s: int = 7,
                         full_page: bool = False, sign_in: bool = True) -> Any:
    """Screenshot a running app. Signs in first when mcp/credentials.json holds that app's login."""
    state = await core.screenshot_app(name_or_url, width, height, wait_s, full_page, sign_in)
    shot = state.get("screenshot")
    if Image and shot and Path(shot).exists():
        return Image(path=shot)
    return state


@mcp.tool()
async def browse_app(name_or_url: str, actions: list[dict], wait_s: int = 6,
                     sign_in: bool = True) -> dict:
    """Drive a running app in a browser and return what the page then says.

    actions run in order, e.g.
      [{"fill": {"label": "Username", "text": "demo"}},
       {"click": "Sign in"}, {"select": {"label": "Category", "option": "FinOps"}},
       {"wait_ms": 3000}, {"press": {"label": "Search", "key": "Enter"}}]
    Slower and more fragile than an API: a layout change breaks the selectors.
    """
    return await core.browse_app(name_or_url, actions, wait_s, sign_in)


@mcp.tool()
async def discover_apps(verify: bool = True, refresh: bool = False, concurrency: int = 6) -> dict:
    """Find which catalogue apps are deployed on Streamlit Cloud and cache their URLs.

    Tries https://<repo>.streamlit.app for every repo, variant and title slug, keeps the ones that
    answer, and (verify=True) opens each in a browser to record running / asleep / no access.
    """
    return await core.discover_apps(verify, refresh, concurrency)


if __name__ == "__main__":
    mcp.run()
