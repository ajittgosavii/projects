"""Local control panel for the same functions the echo-apps MCP server exposes.

Run it with a Python that has Playwright installed (the browser actions need it):

    C:\\aidemos\\.venv\\Scripts\\streamlit.exe run mcp/ui.py --server.port 8533

Streamlit Community Cloud cannot run a browser, so Wake, Screenshot, Browse and the deep
status check only work locally.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]  # streamlit only adds the script's own folder
import core  # noqa: E402  (shared with the MCP server; no MCP dependency)
import auth  # noqa: E402  (repo root: logo + lab name, so both pages look the same)

STATE_ICON = {"running": "🟢 running", "asleep": "😴 asleep", "unknown": "⚪ unknown"}
run = lambda coro: asyncio.run(coro)  # noqa: E731

st.set_page_config(page_title="ECHO App Operations", page_icon="🛠️", layout="wide")
st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@500;600&display=swap');
      :root { --ink:#14213D; --slate:#5B6475; --muted:#6A7386; --rule:#DDE2EA; --navy:#0F2248;
              --body:'IBM Plex Sans','Segoe UI',system-ui,sans-serif;
              --cond:'IBM Plex Sans Condensed','Segoe UI',sans-serif; }
      [data-testid="stElementContainer"]:has(style) { display: none; }
      .block-container { padding-top: 1.5rem !important; max-width: 1500px; }
      .bar { display: flex; align-items: center; gap: 0.75rem; background: var(--navy); color: #fff;
             border-radius: 8px; padding: 0.7rem 1rem; margin-bottom: 1.2rem; font-family: var(--body); }
      .bar .lab { font-family: var(--cond); font-weight: 600; font-size: 1.1rem; line-height: 1.2; }
      .bar .sub { font-size: 0.78rem; color: #9FB0CC; }
      .note { font-family: var(--body); color: var(--muted); font-size: 0.8rem; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    f'<div class="bar">{auth.logo_svg(30, "ops")}<div><div class="lab">App Operations</div>'
    f'<div class="sub">{auth.LAB_NAME} — the same actions the echo-apps MCP server performs</div></div></div>',
    unsafe_allow_html=True,
)

if not core.HAS_PLAYWRIGHT:
    st.warning(f"Playwright is missing from this Python ({sys.executable}), so Wake, Screenshot, Browse "
               f"and the deep status check are disabled. Install it with `{core.NO_BROWSER['fix']}`, "
               "or run this page with the interpreter that has it.")


def apps_frame(apps: dict) -> pd.DataFrame:
    rows = [{"App": a.get("title") or slug, "Slug": slug,
             "State": STATE_ICON.get(a.get("state", "unknown"), a.get("state", "unknown")),
             "Checked": a.get("checked", "—"), "URL": a["url"]}
            for slug, a in sorted(apps.items(), key=lambda kv: (kv[1].get("state") != "running", kv[0]))]
    return pd.DataFrame(rows)


apps = core.known_apps()
if not apps:
    st.warning("No apps discovered yet. Run **Discover apps** below to probe every catalogue name.")

left, right = st.columns([3, 2], gap="large")

with left:
    st.subheader("Deployed apps")
    counts: dict[str, int] = {}
    for a in apps.values():
        counts[a.get("state", "unknown")] = counts.get(a.get("state", "unknown"), 0) + 1
    st.caption(" · ".join(f"{STATE_ICON.get(k, k)}: {v}" for k, v in sorted(counts.items())) or "nothing cached yet")
    if apps:
        st.dataframe(apps_frame(apps), width="stretch", hide_index=True, height=430,
                     column_config={"URL": st.column_config.LinkColumn("URL", display_text="open")})

    with st.expander("Discover apps (probe every catalogue name)"):
        verify = st.checkbox("Also open each one in a browser to read its real state (slower, ~3 min)",
                             value=core.HAS_PLAYWRIGHT, disabled=not core.HAS_PLAYWRIGHT)
        if st.button("Run discovery", type="primary"):
            with st.spinner("Probing Streamlit Cloud…"):
                result = run(core.discover_apps(verify=verify, refresh=True))
            st.success(f"{result['deployed']} deployed — {result['by_state']}")
            st.rerun()

with right:
    st.subheader("Run an action")
    if apps:
        labels = {f'{a.get("title") or s} ({s})': s for s, a in sorted(apps.items())}
        choice = st.selectbox("Application", list(labels), index=0)
        slug = labels[choice]
        st.caption(apps[slug]["url"])
    else:
        slug = st.text_input("App slug or URL", "echoaiprojects")

    action = st.radio("Action", ["Check status", "Wake", "Screenshot", "Browse"], horizontal=True)
    browser_needed = action in ("Wake", "Screenshot", "Browse")
    blocked = browser_needed and not core.HAS_PLAYWRIGHT
    result_box = st.container()

    if action == "Check status":
        deep = st.checkbox("Open it in a browser for the real state", value=core.HAS_PLAYWRIGHT,
                           disabled=not core.HAS_PLAYWRIGHT,
                           help="HTTP alone only proves the URL exists: asleep and private apps both answer 200.")
        if st.button("Check", type="primary"):
            with st.spinner("Checking…"):
                result_box.json(run(core.check_app(slug, deep=deep)))

    elif action == "Wake":
        st.markdown('<p class="note">Clicks “Yes, get this app back up!” and waits for the app to start.</p>',
                    unsafe_allow_html=True)
        if st.button("Wake app", type="primary", disabled=blocked):
            with st.spinner("Waking… this can take a minute"):
                result_box.json(run(core.wake_app(slug)))

    elif action == "Screenshot":
        c1, c2 = st.columns(2)
        width = c1.number_input("Width", 800, 2560, 1440, step=80)
        height = c2.number_input("Height", 600, 2000, 900, step=50)
        full = st.checkbox("Full page", value=False)
        sign_in = st.checkbox("Sign in when credentials are configured", value=True)
        if st.button("Take screenshot", type="primary", disabled=blocked):
            with st.spinner("Loading the app…"):
                out = run(core.screenshot_app(slug, width=int(width), height=int(height),
                                              full_page=full, sign_in=sign_in))
            if out.get("screenshot") and Path(out["screenshot"]).exists():
                result_box.image(out["screenshot"], caption=Path(out["screenshot"]).name, width="stretch")
                result_box.caption(f'state: {out.get("state")}'
                                   + (" · signed in" if out.get("signed_in") else ""))
            else:
                result_box.error(out.get("error") or f'No screenshot: the app is {out.get("state")}.')

    else:  # Browse
        st.markdown('<p class="note">Drive the running app: fill a field, click a button, then read the page.</p>',
                    unsafe_allow_html=True)
        fill_label = st.text_input("Fill field labelled", "")
        fill_text = st.text_input("with text", "")
        click_label = st.text_input("Then click the button labelled", "")
        if st.button("Run", type="primary", disabled=blocked):
            actions: list[dict] = []
            if fill_label:
                actions.append({"fill": {"label": fill_label, "text": fill_text}})
            if click_label:
                actions.append({"click": click_label})
            actions.append({"wait_ms": 2500})
            with st.spinner("Driving the app…"):
                out = run(core.browse_app(slug, actions))
            if out.get("error"):
                result_box.error(out["error"])
                if out.get("buttons_on_page"):
                    result_box.caption("Buttons on the page: " + ", ".join(out["buttons_on_page"]))
            elif out.get("hint"):
                result_box.warning(f'{out.get("state")} — {out["hint"]}')
            else:
                result_box.success("Performed: " + ", ".join(out.get("performed", [])))
            if out.get("screenshot") and Path(out["screenshot"]).exists():
                result_box.image(out["screenshot"], width="stretch")
            if out.get("text"):
                result_box.text_area("Page text", out["text"], height=200)

st.markdown(
    '<p class="note">Wake, Screenshot, Browse and the deep status check drive a real browser, so this page has to '
    "run on your own machine — Streamlit Community Cloud cannot run one. Logins come from mcp/credentials.json.</p>",
    unsafe_allow_html=True,
)
