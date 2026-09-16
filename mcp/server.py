"""MCP server for the ECHO AI Lab Streamlit apps: catalogue, health, wake, screenshot and browse.

Run it directly (stdio):  python mcp/server.py
Register with Claude Code: claude mcp add echo-apps -s user -- python <abs path>/mcp/server.py

Streamlit Community Cloud has no public API, so:
  * the catalogue comes from projects.json (the same data the portfolio page shows);
  * an app's URL is guessed as https://<repo>.streamlit.app and verified, cached in apps.json;
  * HTTP tells you only whether a URL exists (404) — a private app still answers 200, and a
    sleeping app is indistinguishable over HTTP, so the real state needs a browser.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from pathlib import Path
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

try:  # lets screenshots come back as an image the model can see
    from mcp.server.fastmcp import Image
except ImportError:  # pragma: no cover - older SDKs
    Image = None

ROOT = Path(__file__).resolve().parent
CATALOGUE_FILE = ROOT.parent / "projects.json"
APPS_FILE = ROOT / "apps.json"            # cache: slug -> {url, state, title, checked}
CREDS_FILE = ROOT / "credentials.json"    # gitignored: {"slug": {"username": ..., "password": ...}}
SHOTS_DIR = ROOT / "screenshots"

# apps that are deployed but are not rows in the catalogue (the portfolio page itself)
EXTRA_APPS = {"echoaiprojects": {"title": "Application Portfolio (this catalogue)", "repo": "projects"}}
INNER_PATH = "/~/+/"  # the app itself, inside the Streamlit Cloud wrapper page
SLEEP_TEXT = "has gone to sleep"
WAKE_BUTTON = "Yes, get this app back up!"
NO_ACCESS_TEXT = "do not have access to this app"
UA = "Mozilla/5.0 (compatible; echo-apps-mcp/1.0)"

# stdio carries the MCP protocol: keep chatty client logs out of it
for noisy in ("httpx", "httpcore", "urllib3"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

mcp = FastMCP("echo-apps")


# --------------------------------------------------------------------------- data


def _catalogue() -> list[dict]:
    return json.loads(CATALOGUE_FILE.read_text(encoding="utf-8")) if CATALOGUE_FILE.exists() else []


def _known_apps() -> dict[str, dict]:
    return json.loads(APPS_FILE.read_text(encoding="utf-8")) if APPS_FILE.exists() else {}


def _save_apps(apps: dict[str, dict]) -> None:
    APPS_FILE.write_text(json.dumps(apps, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def _credentials(slug: str) -> dict[str, str] | None:
    if not CREDS_FILE.exists():
        return None
    creds = json.loads(CREDS_FILE.read_text(encoding="utf-8"))
    return creds.get(slug) or creds.get(slug.replace("-", "")) or None


def _slugs_for(row: dict) -> list[str]:
    """Candidate Streamlit Cloud subdomains for one catalogue row."""
    names = [row["repo"]] if row.get("repo") else []
    names += row.get("variants", [])
    names.append(re.sub(r"[^a-z0-9]", "", row["title"].lower())[:30])
    return list(dict.fromkeys(n.replace("_", "-").lower() for n in names if n))


def _resolve(name_or_url: str) -> tuple[str, str]:
    """Return (slug, url) for a URL, a known app name, a repo name or a catalogue title."""
    value = name_or_url.strip()
    if value.startswith("http"):
        slug = re.sub(r"^https?://([^.]+)\..*$", r"\1", value)
        return slug, value.rstrip("/")
    apps, key = _known_apps(), value.lower().replace("_", "-")
    if key in apps:
        return key, apps[key]["url"]
    for row in _catalogue():  # match a catalogue title, then fall back to its repo slug
        if row["title"].lower() == value.lower() or (row.get("repo") or "").lower() == key:
            for slug in _slugs_for(row):
                if slug in apps:
                    return slug, apps[slug]["url"]
            slug = _slugs_for(row)[0]
            return slug, f"https://{slug}.streamlit.app"
    return key, f"https://{key}.streamlit.app"


def _row_for(slug: str) -> dict | None:
    for row in _catalogue():
        if slug in _slugs_for(row):
            return row
    return None


# --------------------------------------------------------------------------- probing


async def _http_state(client: httpx.AsyncClient, url: str) -> dict:
    started = time.perf_counter()
    try:
        r = await client.get(url, follow_redirects=True, timeout=30)
        return {"http": r.status_code, "exists": r.status_code == 200,
                "ms": round((time.perf_counter() - started) * 1000)}
    except Exception as exc:
        return {"http": None, "exists": False, "error": f"{type(exc).__name__}: {exc}",
                "ms": round((time.perf_counter() - started) * 1000)}


async def _open_app(page, url: str, wait_s: int = 7) -> tuple[str, str]:
    """Load an app and return (state, page text).

    A bare *.streamlit.app address is a wrapper page: it draws the "gone to sleep" and "no access"
    screens itself, but embeds a *running* app in an iframe, leaving the top-level body empty. So a
    running app is reopened at its inner URL, where its own controls can be read and driven.
    """
    try:
        await page.goto(url, wait_until="networkidle", timeout=60_000)
    except Exception:
        pass
    await page.wait_for_timeout(wait_s * 1000)
    text = " ".join((await page.inner_text("body")).split())
    if SLEEP_TEXT in text:
        return "asleep", text
    if NO_ACCESS_TEXT in text:
        return "no access (private, signed-out, or deleted)", text
    if not text.strip():
        try:
            await page.goto(url.rstrip("/") + INNER_PATH, wait_until="networkidle", timeout=60_000)
            await page.wait_for_timeout(wait_s * 1000)
            text = " ".join((await page.inner_text("body")).split())
        except Exception:
            pass
    return "running", text


async def _sign_in(page, slug: str, settle_ms: int = 6000) -> bool:
    """Sign in when mcp/credentials.json has this app's login and a login form appears."""
    creds = _credentials(slug)
    if not creds:
        return False
    box = page.get_by_role("textbox", name="Username")
    try:  # the form can take a few seconds to render over the websocket
        await box.wait_for(state="visible", timeout=20_000)
    except Exception:
        return False
    await box.fill(creds["username"])
    await page.get_by_role("textbox", name="Password").fill(creds["password"])
    await page.get_by_role("button", name="Sign in").click()
    await page.wait_for_timeout(settle_ms)
    return True


async def _browser_state(url: str, slug: str = "", wait_s: int = 7, sign_in: bool = True,
                         shot: Path | None = None, full_page: bool = False,
                         size: tuple[int, int] = (1440, 900)) -> dict:
    """Load the app in a headless browser and report what is actually on screen."""
    from playwright.async_api import async_playwright

    out: dict[str, Any] = {"url": url}
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": size[0], "height": size[1]})
        try:
            state, text = await _open_app(page, url, wait_s)
            if state == "running" and sign_in and await _sign_in(page, slug):
                text = " ".join((await page.inner_text("body")).split())
                out["signed_in"] = True
            out["state"] = state
            out["title"] = await page.title()
            out["text"] = text[:1200]
            if shot:
                shot.parent.mkdir(parents=True, exist_ok=True)
                await page.screenshot(path=str(shot), full_page=full_page)
                out["screenshot"] = str(shot)
        finally:
            await browser.close()
    return out


# --------------------------------------------------------------------------- tools


@mcp.tool()
async def list_apps(pillar: str = "", category: str = "", query: str = "",
                    deployed_only: bool = False, limit: int = 40) -> str:
    """List the lab's applications from the portfolio catalogue.

    pillar/category filter exactly (case-insensitive); query matches title, description or stack.
    deployed_only keeps apps with a known Streamlit Cloud URL (run discover_apps first).
    """
    apps, rows = _known_apps(), _catalogue()
    out = []
    for row in rows:
        if pillar and row["hexagon"].lower() != pillar.lower():
            continue
        if category and row["category"].lower() != category.lower():
            continue
        hay = f'{row["title"]} {row["description"]} {" ".join(row["stack"])}'.lower()
        if query and query.lower() not in hay:
            continue
        url = next((apps[s]["url"] for s in _slugs_for(row) if s in apps), None)
        if deployed_only and not url:
            continue
        out.append({"title": row["title"], "pillar": row["hexagon"], "category": row["category"],
                    "repo": row.get("repo"), "url": url})
    lines = [f'{len(out)} application(s)' + (f" (showing {limit})" if len(out) > limit else "")]
    for a in out[:limit]:
        lines.append(f'- {a["title"]} — {a["pillar"]} / {a["category"]}'
                     + (f' — {a["url"]}' if a["url"] else " — no deployed URL known"))
    return "\n".join(lines)


@mcp.tool()
async def get_app(name: str) -> dict:
    """Full catalogue entry for one application, plus its Streamlit Cloud URL if known."""
    slug, url = _resolve(name)
    row = _row_for(slug) or next((r for r in _catalogue() if r["title"].lower() == name.strip().lower()), None)
    if not row:
        return {"error": f"No catalogue entry matches {name!r}", "guessed_url": url}
    known = _known_apps().get(slug)
    return {**row, "slug": slug, "url": (known or {}).get("url", url),
            "last_known_state": (known or {}).get("state")}


@mcp.tool()
async def check_app(name_or_url: str, deep: bool = True) -> dict:
    """Is the app up, asleep, private or missing?

    HTTP alone only proves the URL exists (404 = no such app); a sleeping or private app still
    answers 200, so deep=True (default) opens it in a headless browser to read the real state.
    """
    slug, url = _resolve(name_or_url)
    async with httpx.AsyncClient(headers={"User-Agent": UA}) as client:
        result = {"slug": slug, **await _http_state(client, url), "url": url}
    if result["http"] == 404:
        result["state"] = "not deployed (404)"
        return result
    if deep and result["exists"]:
        result.update(await _browser_state(url, slug, sign_in=False))
    return result


@mcp.tool()
async def wake_app(name_or_url: str, timeout_s: int = 150) -> dict:
    """Wake a sleeping Streamlit Cloud app by clicking 'Yes, get this app back up!' and wait for it."""
    from playwright.async_api import async_playwright

    slug, url = _resolve(name_or_url)
    started = time.perf_counter()
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        try:
            await page.goto(url, wait_until="networkidle", timeout=60_000)
            await page.wait_for_timeout(5000)
            text = " ".join((await page.inner_text("body")).split())
            if SLEEP_TEXT not in text:
                state = "no access" if NO_ACCESS_TEXT in text else "already running"
                return {"slug": slug, "url": url, "state": state, "woke": False}
            await page.get_by_role("button", name=WAKE_BUTTON).click()
            while time.perf_counter() - started < timeout_s:
                await page.wait_for_timeout(5000)
                text = " ".join((await page.inner_text("body")).split())
                if SLEEP_TEXT not in text and "in the oven" not in text.lower():
                    return {"slug": slug, "url": url, "state": "running", "woke": True,
                            "seconds": round(time.perf_counter() - started)}
            return {"slug": slug, "url": url, "state": "still waking", "woke": False,
                    "seconds": round(time.perf_counter() - started)}
        finally:
            await browser.close()


@mcp.tool()
async def screenshot_app(name_or_url: str, width: int = 1440, height: int = 900, wait_s: int = 7,
                         full_page: bool = False, sign_in: bool = True) -> Any:
    """Screenshot a running app. Signs in first when mcp/credentials.json holds that app's login."""
    slug, url = _resolve(name_or_url)
    path = SHOTS_DIR / f"{slug}-{int(time.time())}.png"
    state = await _browser_state(url, slug, wait_s=wait_s, sign_in=sign_in, shot=path,
                                 full_page=full_page, size=(width, height))
    if Image and path.exists():
        return Image(path=str(path))
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
    from playwright.async_api import async_playwright

    slug, url = _resolve(name_or_url)
    done, path = [], SHOTS_DIR / f"{slug}-browse-{int(time.time())}.png"
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            state, _ = await _open_app(page, url, wait_s)
            if state != "running":
                return {"slug": slug, "url": url, "state": state, "performed": [],
                        "hint": "run wake_app first" if state == "asleep" else "check access to this app"}
            if sign_in and await _sign_in(page, slug):
                done.append("signed in")
            for action in actions:
                if "fill" in action:
                    a = action["fill"]
                    await page.get_by_role("textbox", name=a["label"]).fill(a["text"])
                elif "click" in action:
                    label = action["click"]
                    target = page.get_by_role("button", name=label).first
                    if not await target.count():
                        target = page.get_by_text(label, exact=True).first
                    try:
                        await target.click(timeout=15_000)
                    except Exception as exc:  # report what is on the page instead of raising
                        buttons = await page.get_by_role("button").all_inner_texts()
                        return {"slug": slug, "url": url, "performed": done,
                                "error": f"could not click {label!r}: {type(exc).__name__}",
                                "buttons_on_page": [b for b in buttons if b.strip()][:25],
                                "text": " ".join((await page.inner_text("body")).split())[:1500]}
                elif "select" in action:
                    a = action["select"]
                    await page.get_by_label(a["label"]).select_option(label=a["option"])
                elif "press" in action:
                    a = action["press"]
                    await page.get_by_role("textbox", name=a["label"]).press(a["key"])
                elif "wait_ms" in action:
                    await page.wait_for_timeout(int(action["wait_ms"]))
                else:
                    done.append(f"skipped unknown action {list(action)}")
                    continue
                await page.wait_for_timeout(2500)
                done.append(str(action))
            text = " ".join((await page.inner_text("body")).split())
            path.parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(path))
            return {"slug": slug, "url": url, "performed": done, "screenshot": str(path),
                    "text": text[:3000]}
        finally:
            await browser.close()


@mcp.tool()
async def discover_apps(verify: bool = True, refresh: bool = False, concurrency: int = 6) -> dict:
    """Find which catalogue apps are deployed on Streamlit Cloud and cache their URLs.

    Tries https://<repo>.streamlit.app for every repo, variant and title slug, keeps the ones that
    answer, and (verify=True) opens each in a browser to record running / asleep / no access.
    """
    apps = {} if refresh else _known_apps()
    candidates = {s: row for row in _catalogue() for s in _slugs_for(row)}
    candidates.update({s: r for s, r in EXTRA_APPS.items() if s not in candidates})
    async with httpx.AsyncClient(headers={"User-Agent": UA}) as client:
        sem = asyncio.Semaphore(16)

        async def probe(slug: str) -> tuple[str, dict] | None:
            async with sem:
                st = await _http_state(client, f"https://{slug}.streamlit.app")
            return (slug, st) if st["exists"] else None

        found = [r for r in await asyncio.gather(*(probe(s) for s in candidates)) if r]

    for slug, st in found:
        row = candidates[slug]
        apps[slug] = {"url": f"https://{slug}.streamlit.app", "title": row["title"],
                      "repo": row.get("repo"), "state": apps.get(slug, {}).get("state", "unknown")}

    if verify:
        sem = asyncio.Semaphore(concurrency)

        async def verify_one(slug: str) -> None:
            async with sem:
                state = await _browser_state(apps[slug]["url"], slug, wait_s=6, sign_in=False)
            apps[slug].update(state=state.get("state", "unknown"), checked=time.strftime("%Y-%m-%d %H:%M"))

        await asyncio.gather(*(verify_one(s) for s in list(apps)))

    _save_apps(apps)
    by_state: dict[str, int] = {}
    for a in apps.values():
        by_state[a.get("state", "unknown")] = by_state.get(a.get("state", "unknown"), 0) + 1
    return {"deployed": len(apps), "by_state": by_state, "cache": str(APPS_FILE),
            "apps": {s: {"url": a["url"], "state": a.get("state")} for s, a in sorted(apps.items())}}


if __name__ == "__main__":
    mcp.run()
