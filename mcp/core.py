"""Everything the echo-apps tools do, with no MCP or Streamlit dependency.

server.py wraps these as MCP tools; ui.py calls them from a local Streamlit page. Keeping the
logic here means the UI needs neither the MCP SDK nor its pydantic version.

Streamlit Community Cloud has no public API, so:
  * the catalogue comes from projects.json (the same data the portfolio page shows);
  * an app's URL is guessed as https://<repo>.streamlit.app and verified, cached in apps.json;
  * HTTP tells you only whether a URL exists (404) — a private app still answers 200, and a
    sleeping app is indistinguishable over HTTP, so the real state needs a browser.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import re
import time
from pathlib import Path
from typing import Any

import httpx

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

def _playwright_ready() -> bool:
    """A half-removed install leaves an empty `playwright` folder that imports as a namespace
    package, so check for the module we actually use, not just the top-level name."""
    try:
        return importlib.util.find_spec("playwright.async_api") is not None
    except (ImportError, AttributeError, ValueError):
        return False


HAS_PLAYWRIGHT = _playwright_ready()
NO_BROWSER = {"error": "Playwright is not installed in this Python, so browser actions are unavailable.",
              "fix": "pip install playwright && python -m playwright install chromium"}


# --------------------------------------------------------------------------- catalogue


def catalogue() -> list[dict]:
    return json.loads(CATALOGUE_FILE.read_text(encoding="utf-8")) if CATALOGUE_FILE.exists() else []


def known_apps() -> dict[str, dict]:
    return json.loads(APPS_FILE.read_text(encoding="utf-8")) if APPS_FILE.exists() else {}


def save_apps(apps: dict[str, dict]) -> None:
    APPS_FILE.write_text(json.dumps(apps, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def credentials(slug: str) -> dict[str, str] | None:
    if not CREDS_FILE.exists():
        return None
    creds = json.loads(CREDS_FILE.read_text(encoding="utf-8"))
    return creds.get(slug) or creds.get(slug.replace("-", "")) or None


def slugs_for(row: dict) -> list[str]:
    """Candidate Streamlit Cloud subdomains for one catalogue row."""
    names = [row["repo"]] if row.get("repo") else []
    names += row.get("variants", [])
    names.append(re.sub(r"[^a-z0-9]", "", row["title"].lower())[:30])
    return list(dict.fromkeys(n.replace("_", "-").lower() for n in names if n))


def resolve(name_or_url: str) -> tuple[str, str]:
    """Return (slug, url) for a URL, a known app name, a repo name or a catalogue title."""
    value = name_or_url.strip()
    if value.startswith("http"):
        slug = re.sub(r"^https?://([^.]+)\..*$", r"\1", value)
        return slug, value.rstrip("/")
    apps, key = known_apps(), value.lower().replace("_", "-")
    if key in apps:
        return key, apps[key]["url"]
    for row in catalogue():  # match a catalogue title, then fall back to its repo slug
        if row["title"].lower() == value.lower() or (row.get("repo") or "").lower() == key:
            for slug in slugs_for(row):
                if slug in apps:
                    return slug, apps[slug]["url"]
            slug = slugs_for(row)[0]
            return slug, f"https://{slug}.streamlit.app"
    return key, f"https://{key}.streamlit.app"


def row_for(slug: str) -> dict | None:
    for row in catalogue():
        if slug in slugs_for(row):
            return row
    return None


# --------------------------------------------------------------------------- probing


async def http_state(client: httpx.AsyncClient, url: str) -> dict:
    started = time.perf_counter()
    try:
        r = await client.get(url, follow_redirects=True, timeout=30)
        return {"http": r.status_code, "exists": r.status_code == 200,
                "ms": round((time.perf_counter() - started) * 1000)}
    except Exception as exc:
        return {"http": None, "exists": False, "error": f"{type(exc).__name__}: {exc}",
                "ms": round((time.perf_counter() - started) * 1000)}


async def open_app(page, url: str, wait_s: int = 7) -> tuple[str, str]:
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


async def sign_in_if_configured(page, slug: str, settle_ms: int = 6000) -> bool:
    """Sign in when mcp/credentials.json has this app's login and a login form appears."""
    creds = credentials(slug)
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


async def browser_state(url: str, slug: str = "", wait_s: int = 7, sign_in: bool = True,
                        shot: Path | None = None, full_page: bool = False,
                        size: tuple[int, int] = (1440, 900)) -> dict:
    """Load the app in a headless browser and report what is actually on screen."""
    if not HAS_PLAYWRIGHT:
        return {"url": url, "state": "unknown", **NO_BROWSER}
    from playwright.async_api import async_playwright

    out: dict[str, Any] = {"url": url}
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": size[0], "height": size[1]})
        try:
            state, text = await open_app(page, url, wait_s)
            if state == "running" and sign_in and await sign_in_if_configured(page, slug):
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


# --------------------------------------------------------------------------- actions


async def list_apps(pillar: str = "", category: str = "", query: str = "",
                    deployed_only: bool = False, limit: int = 40) -> str:
    """Catalogue listing as text, filtered by pillar, category or free text."""
    apps, rows = known_apps(), catalogue()
    out = []
    for row in rows:
        if pillar and row["hexagon"].lower() != pillar.lower():
            continue
        if category and row["category"].lower() != category.lower():
            continue
        hay = f'{row["title"]} {row["description"]} {" ".join(row["stack"])}'.lower()
        if query and query.lower() not in hay:
            continue
        url = next((apps[s]["url"] for s in slugs_for(row) if s in apps), None)
        if deployed_only and not url:
            continue
        out.append({"title": row["title"], "pillar": row["hexagon"], "category": row["category"],
                    "repo": row.get("repo"), "url": url})
    lines = [f"{len(out)} application(s)" + (f" (showing {limit})" if len(out) > limit else "")]
    for a in out[:limit]:
        lines.append(f'- {a["title"]} — {a["pillar"]} / {a["category"]}'
                     + (f' — {a["url"]}' if a["url"] else " — no deployed URL known"))
    return "\n".join(lines)


async def get_app(name: str) -> dict:
    """Full catalogue entry for one application, plus its Streamlit Cloud URL if known."""
    slug, url = resolve(name)
    row = row_for(slug) or next((r for r in catalogue() if r["title"].lower() == name.strip().lower()), None)
    if not row:
        return {"error": f"No catalogue entry matches {name!r}", "guessed_url": url}
    known = known_apps().get(slug)
    return {**row, "slug": slug, "url": (known or {}).get("url", url),
            "last_known_state": (known or {}).get("state")}


async def check_app(name_or_url: str, deep: bool = True) -> dict:
    """Is the app up, asleep, private or missing? HTTP first, then the browser for the real state."""
    slug, url = resolve(name_or_url)
    async with httpx.AsyncClient(headers={"User-Agent": UA}) as client:
        result = {"slug": slug, **await http_state(client, url), "url": url}
    if result["http"] == 404:
        result["state"] = "not deployed (404)"
        return result
    if deep and result["exists"]:
        result.update(await browser_state(url, slug, sign_in=False))
    return result


async def wake_app(name_or_url: str, timeout_s: int = 150) -> dict:
    """Wake a sleeping app by clicking 'Yes, get this app back up!' and wait for it to start."""
    slug, url = resolve(name_or_url)
    if not HAS_PLAYWRIGHT:
        return {"slug": slug, "url": url, "woke": False, **NO_BROWSER}
    from playwright.async_api import async_playwright

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


async def screenshot_app(name_or_url: str, width: int = 1440, height: int = 900, wait_s: int = 7,
                         full_page: bool = False, sign_in: bool = True) -> dict:
    """Screenshot a running app; returns the state plus the saved file path."""
    slug, url = resolve(name_or_url)
    if not HAS_PLAYWRIGHT:
        return {"slug": slug, "url": url, **NO_BROWSER}
    path = SHOTS_DIR / f"{slug}-{int(time.time())}.png"
    return await browser_state(url, slug, wait_s=wait_s, sign_in=sign_in, shot=path,
                               full_page=full_page, size=(width, height))


async def browse_app(name_or_url: str, actions: list[dict], wait_s: int = 6,
                     sign_in: bool = True) -> dict:
    """Drive a running app in a browser and return what the page then says."""
    slug, url = resolve(name_or_url)
    if not HAS_PLAYWRIGHT:
        return {"slug": slug, "url": url, "performed": [], **NO_BROWSER}
    from playwright.async_api import async_playwright

    done, path = [], SHOTS_DIR / f"{slug}-browse-{int(time.time())}.png"
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            state, _ = await open_app(page, url, wait_s)
            if state != "running":
                return {"slug": slug, "url": url, "state": state, "performed": [],
                        "hint": "run wake_app first" if state == "asleep" else "check access to this app"}
            if sign_in and await sign_in_if_configured(page, slug):
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


async def discover_apps(verify: bool = True, refresh: bool = False, concurrency: int = 6) -> dict:
    """Probe https://<slug>.streamlit.app for every catalogue name, cache what answers."""
    apps = {} if refresh else known_apps()
    candidates = {s: row for row in catalogue() for s in slugs_for(row)}
    candidates.update({s: r for s, r in EXTRA_APPS.items() if s not in candidates})
    async with httpx.AsyncClient(headers={"User-Agent": UA}) as client:
        sem = asyncio.Semaphore(16)

        async def probe(slug: str) -> tuple[str, dict] | None:
            async with sem:
                st = await http_state(client, f"https://{slug}.streamlit.app")
            return (slug, st) if st["exists"] else None

        found = [r for r in await asyncio.gather(*(probe(s) for s in candidates)) if r]

    for slug, st in found:
        row = candidates[slug]
        apps[slug] = {"url": f"https://{slug}.streamlit.app", "title": row["title"],
                      "repo": row.get("repo"), "state": apps.get(slug, {}).get("state", "unknown")}

    if verify and HAS_PLAYWRIGHT:
        sem = asyncio.Semaphore(concurrency)

        async def verify_one(slug: str) -> None:
            async with sem:
                state = await browser_state(apps[slug]["url"], slug, wait_s=6, sign_in=False)
            apps[slug].update(state=state.get("state", "unknown"), checked=time.strftime("%Y-%m-%d %H:%M"))

        await asyncio.gather(*(verify_one(s) for s in list(apps)))

    save_apps(apps)
    by_state: dict[str, int] = {}
    for a in apps.values():
        by_state[a.get("state", "unknown")] = by_state.get(a.get("state", "unknown"), 0) + 1
    out = {"deployed": len(apps), "by_state": by_state, "cache": str(APPS_FILE),
           "apps": {s: {"url": a["url"], "state": a.get("state")} for s, a in sorted(apps.items())}}
    if verify and not HAS_PLAYWRIGHT:
        out["note"] = NO_BROWSER["error"] + " States were left as they were."
    return out
