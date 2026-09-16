"""Local control panel for the same functions the echo-apps MCP server exposes.

Run it with a Python that has Playwright installed (the browser actions need it):

    C:\\aidemos\\.venv\\Scripts\\streamlit.exe run mcp/ui.py --server.port 8533

Streamlit Community Cloud cannot run a browser, so Wake, Screenshot, Browse and the deep
status check only work locally.
"""

from __future__ import annotations

import asyncio
import html
import json
import sys
from pathlib import Path

import streamlit as st

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]  # streamlit only adds the script's own folder
import core  # noqa: E402  (shared with the MCP server; no MCP dependency)
import auth  # noqa: E402  (repo root: logo + lab name, so both pages look the same)

# state -> (colour, label). Colour never carries the meaning on its own: every chip has its word.
STATES = {
    "running": ("#0ca30c", "Running"),
    "asleep": ("#5B6475", "Asleep"),
    "no access (private, signed-out, or deleted)": ("#d03b3b", "No access"),
    "not deployed (404)": ("#d03b3b", "Not deployed"),
    "unknown": ("#C3C2B7", "Unknown"),
}
ACTIONS = ["Check status", "Wake", "Screenshot", "Browse"]
run = lambda coro: asyncio.run(coro)  # noqa: E731
esc = lambda v: html.escape(str(v))  # noqa: E731

st.set_page_config(page_title="App Operations — ECHO AI Lab", page_icon="🛠️", layout="wide")

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@500;600&display=swap');
      :root { --ink:#14213D; --slate:#5B6475; --muted:#6A7386; --rule:#DDE2EA; --rule-soft:#E8ECF2;
              --canvas:#F7F8FA; --head:#EEF1F5; --link:#1F5FBF; --navy:#0F2248; --gutter:2.5rem;
              --body:'IBM Plex Sans','Segoe UI',system-ui,sans-serif;
              --cond:'IBM Plex Sans Condensed','Segoe UI',sans-serif; }
      [data-testid="stHeader"] { display: none; }
      [data-testid="stElementContainer"]:has(style) { display: none; }
      footer { visibility: hidden; }
      .block-container { max-width: none; padding: 0 var(--gutter) 3rem !important; }
      html, body, [data-testid="stAppViewContainer"] { font-family: var(--body); }

      /* app bar */
      .st-key-appbar { background: var(--navy); width: calc(100% + 2 * var(--gutter)) !important;
                       max-width: none !important; margin: 0 calc(-1 * var(--gutter)) 1.6rem !important;
                       padding: 0.7rem var(--gutter); box-sizing: border-box; }
      .st-key-appbar [data-testid="stHorizontalBlock"] { max-width: 1560px; margin: 0 auto; }
      .lockup { display: flex; align-items: center; gap: 0.75rem; }
      .lockup .lab { font-family: var(--cond); font-weight: 600; font-size: 1.12rem; color: #fff; line-height: 1.2; }
      .lockup .sub { font-size: 0.78rem; color: #9FB0CC; }
      .envchip { text-align: right; font-size: 0.78rem; color: #BFCAE0; line-height: 1.5; }
      .envchip b { color: #fff; font-weight: 600; }
      .envchip .dot { display: inline-block; width: 0.5rem; height: 0.5rem; border-radius: 50%;
                      margin-right: 0.35rem; }

      .shell { max-width: 1560px; margin: 0 auto; }
      .banner { display: flex; gap: 0.6rem; align-items: flex-start; background: #FFF8E8;
                border: 1px solid #F3DFAE; border-left: 3px solid #fab219; border-radius: 6px;
                padding: 0.7rem 0.9rem; margin-bottom: 1.1rem; font-size: 0.85rem; color: #4A3D1C; }
      .banner code { background: rgba(0,0,0,0.05); padding: 0 0.25rem; border-radius: 3px; font-size: 0.8rem; }

      .card { background: #fff; border: 1px solid var(--rule); border-radius: 8px; padding: 1rem 1.15rem; }
      .card-head { display: flex; justify-content: space-between; align-items: baseline; gap: 1rem;
                   margin-bottom: 0.8rem; }
      .card-title { font-family: var(--cond); font-weight: 600; font-size: 1.05rem; color: var(--ink); }
      .card-note { font-size: 0.8rem; color: var(--slate); }

      /* fleet strip */
      .fleetbar { display: flex; gap: 2px; height: 12px; margin-bottom: 0.75rem; }
      .fleetbar span { flex: var(--n) 1 0; min-width: 6px; background: var(--c); }
      .fleetbar span:first-child { border-radius: 3px 0 0 3px; }
      .fleetbar span:last-child { border-radius: 0 3px 3px 0; }
      .fleetkey { display: flex; flex-wrap: wrap; gap: 0.4rem 1.6rem; font-size: 0.85rem; color: var(--ink); }
      .fleetkey b { font-variant-numeric: tabular-nums; }

      /* apps table */
      .wrap { border: 1px solid var(--rule); border-radius: 8px; background: #fff; overflow: hidden; }
      table.apps { width: 100%; border-collapse: collapse; font-size: 0.86rem; color: var(--ink);
                   table-layout: fixed; }
      table.apps th { font-family: var(--cond); font-weight: 600; font-size: 0.82rem; color: #3E4859;
                      text-align: left; background: var(--head); padding: 0.6rem 0.8rem;
                      border-bottom: 1px solid var(--rule); }
      table.apps td { padding: 0.6rem 0.8rem; border-bottom: 1px solid var(--rule-soft);
                      overflow-wrap: break-word; }
      table.apps tbody tr:last-child td { border-bottom: 0; }
      table.apps tbody tr:hover td { background: #F6F8FC; }
      table.apps td.name { font-weight: 600; }
      table.apps td.slug, table.apps td.when { color: var(--muted); font-size: 0.8rem; }
      table.apps td.open a { color: var(--link); text-decoration: none; }
      table.apps td.open a:hover { text-decoration: underline; }
      .chip { display: inline-flex; align-items: center; gap: 0.4rem; white-space: nowrap; }
      .chip .dot { width: 0.55rem; height: 0.55rem; border-radius: 50%; background: var(--c); flex: none; }
      .scroll { max-height: 27rem; overflow-y: auto; }

      /* results */
      .result pre { background: var(--canvas); border: 1px solid var(--rule); border-radius: 6px;
                    padding: 0.7rem 0.8rem; font-size: 0.78rem; max-height: 22rem; overflow: auto; }
      .ok { color: #1a6b1a; font-size: 0.85rem; }
      .bad { color: #a32020; font-size: 0.85rem; }
      .note { color: var(--muted); font-size: 0.8rem; }
      [data-testid="stImage"] img { border: 1px solid var(--rule); border-radius: 6px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def state_bits(state: str | None) -> tuple[str, str]:
    return STATES.get(state or "unknown", ("#C3C2B7", (state or "unknown").title()))


def chip(state: str | None) -> str:
    colour, label = state_bits(state)
    return f'<span class="chip" style="--c:{colour}"><span class="dot"></span>{esc(label)}</span>'


# --------------------------------------------------------------------------- app bar

with st.container(key="appbar"):
    left, right = st.columns([6, 3], vertical_alignment="center")
    left.markdown(
        f'<div class="lockup">{auth.logo_svg(32, "ops")}<div><div class="lab">App Operations</div>'
        f'<div class="sub">{auth.LAB_NAME} — the actions the echo-apps MCP server performs</div></div></div>',
        unsafe_allow_html=True,
    )
    ready = core.HAS_PLAYWRIGHT
    right.markdown(
        f'<div class="envchip"><span class="dot" style="background:{"#0ca30c" if ready else "#fab219"}"></span>'
        f'{"Browser actions ready" if ready else "Browser actions unavailable"}<br>'
        f'<b>Python {sys.version.split()[0]}</b></div>',
        unsafe_allow_html=True,
    )

if not core.HAS_PLAYWRIGHT:
    st.markdown(
        '<div class="shell"><div class="banner"><div>⚠️</div><div>Playwright is missing from this Python, so '
        'Wake, Screenshot, Browse and the deep status check are switched off. Install it with '
        f'<code>{esc(core.NO_BROWSER["fix"])}</code>, or start this page with the interpreter that has it.'
        "</div></div></div>",
        unsafe_allow_html=True,
    )

apps = core.known_apps()
counts: dict[str, int] = {}
for a in apps.values():
    counts[a.get("state", "unknown")] = counts.get(a.get("state", "unknown"), 0) + 1

# --------------------------------------------------------------------------- fleet strip

if apps:
    segs = "".join(f'<span style="--c:{state_bits(s)[0]};--n:{n}" title="{esc(state_bits(s)[1])}: {n}"></span>'
                   for s, n in sorted(counts.items(), key=lambda kv: -kv[1]))
    keys = "".join(f'<span class="chip" style="--c:{state_bits(s)[0]}"><span class="dot"></span>'
                   f'{esc(state_bits(s)[1])} <b>{n}</b></span>'
                   for s, n in sorted(counts.items(), key=lambda kv: -kv[1]))
    st.markdown(
        f'<div class="shell"><div class="card"><div class="card-head">'
        f'<span class="card-title">Fleet</span>'
        f'<span class="card-note">{len(apps)} deployed apps on Streamlit Cloud</span></div>'
        f'<div class="fleetbar">{segs}</div><div class="fleetkey">{keys}</div></div></div>',
        unsafe_allow_html=True,
    )
else:
    st.warning("No apps discovered yet — run **Discover apps** on the right to probe every catalogue name.")

st.write("")
table_col, action_col = st.columns([3, 2], gap="large")

# --------------------------------------------------------------------------- apps table

with table_col:
    f1, f2 = st.columns([2, 3], vertical_alignment="bottom")
    query = f1.text_input("Filter", placeholder="Filter by name or slug", label_visibility="collapsed")
    wanted = f2.pills("States", [state_bits(s)[1] for s in sorted(counts, key=lambda s: -counts[s])],
                      selection_mode="multi", key="state_filter", label_visibility="collapsed")

    rows = sorted(apps.items(), key=lambda kv: (kv[1].get("state") != "running", kv[0]))
    if query:
        q = query.lower()
        rows = [(s, a) for s, a in rows if q in s.lower() or q in (a.get("title", "") or "").lower()]
    if wanted:
        rows = [(s, a) for s, a in rows if state_bits(a.get("state"))[1] in wanted]

    body = "".join(
        f'<tr><td class="name">{esc(a.get("title") or s)}</td><td class="slug">{esc(s)}</td>'
        f'<td>{chip(a.get("state"))}</td><td class="when">{esc(a.get("checked", "—"))}</td>'
        f'<td class="open"><a href="{esc(a["url"])}" target="_blank" rel="noopener">open ↗</a></td></tr>'
        for s, a in rows
    )
    st.markdown(
        f'<div class="card-head"><span class="card-title">Deployed apps</span>'
        f'<span class="card-note">showing {len(rows)} of {len(apps)}</span></div>'
        '<div class="wrap scroll"><table class="apps"><colgroup><col style="width:38%"><col style="width:20%">'
        '<col style="width:16%"><col style="width:17%"><col style="width:9%"></colgroup>'
        "<thead><tr><th>Application</th><th>Slug</th><th>State</th><th>Checked</th><th></th></tr></thead>"
        f"<tbody>{body or '<tr><td colspan=5 class=note>Nothing matches this filter.</td></tr>'}</tbody>"
        "</table></div>",
        unsafe_allow_html=True,
    )

    with st.expander("Discover apps — probe every catalogue name for a Streamlit Cloud URL"):
        verify = st.checkbox("Also open each one in a browser to read its real state (about 3 minutes)",
                             value=core.HAS_PLAYWRIGHT, disabled=not core.HAS_PLAYWRIGHT)
        if st.button("Run discovery", type="primary"):
            with st.spinner("Probing Streamlit Cloud…"):
                result = run(core.discover_apps(verify=verify, refresh=True))
            st.success(f"{result['deployed']} deployed — " +
                       ", ".join(f"{state_bits(k)[1]}: {v}" for k, v in result["by_state"].items()))
            st.rerun()

# --------------------------------------------------------------------------- actions

with action_col:
    st.markdown('<div class="card-head"><span class="card-title">Run an action</span></div>',
                unsafe_allow_html=True)
    if apps:
        labels = {f'{a.get("title") or s}  ·  {s}': s for s, a in sorted(apps.items())}
        slug = labels[st.selectbox("Application", list(labels))]
        current = apps[slug]
        st.markdown(f'<p class="note">{chip(current.get("state"))} &nbsp;·&nbsp; '
                    f'<a href="{esc(current["url"])}" target="_blank">{esc(current["url"])}</a></p>',
                    unsafe_allow_html=True)
    else:
        slug = st.text_input("App slug or URL", "echoaiprojects")

    action = st.segmented_control("Action", ACTIONS, default=ACTIONS[0], key="action",
                                  label_visibility="collapsed") or ACTIONS[0]
    blocked = action in ("Wake", "Screenshot", "Browse") and not core.HAS_PLAYWRIGHT
    out: dict | None = None

    if action == "Check status":
        deep = st.checkbox("Open it in a browser for the real state", value=core.HAS_PLAYWRIGHT,
                           disabled=not core.HAS_PLAYWRIGHT,
                           help="HTTP alone only proves the URL exists: asleep and private apps both answer 200.")
        if st.button("Check status", type="primary", width="stretch"):
            with st.spinner("Checking…"):
                out = run(core.check_app(slug, deep=deep))

    elif action == "Wake":
        st.markdown('<p class="note">Clicks “Yes, get this app back up!” and waits for the app to start, '
                    "usually 15 to 60 seconds.</p>", unsafe_allow_html=True)
        if st.button("Wake app", type="primary", width="stretch", disabled=blocked):
            with st.spinner("Waking…"):
                out = run(core.wake_app(slug))

    elif action == "Screenshot":
        c1, c2 = st.columns(2)
        width = c1.number_input("Width", 800, 2560, 1440, step=80)
        height = c2.number_input("Height", 600, 2000, 900, step=50)
        c3, c4 = st.columns(2)
        full = c3.checkbox("Full page")
        sign_in = c4.checkbox("Sign in if configured", value=True)
        if st.button("Take screenshot", type="primary", width="stretch", disabled=blocked):
            with st.spinner("Loading the app…"):
                out = run(core.screenshot_app(slug, width=int(width), height=int(height),
                                              full_page=full, sign_in=sign_in))

    else:  # Browse
        st.markdown('<p class="note">Drive a running app: fill a field, click a button, then read the page.</p>',
                    unsafe_allow_html=True)
        fill_label = st.text_input("Fill the field labelled")
        fill_text = st.text_input("with this text")
        click_label = st.text_input("Then click the button labelled")
        if st.button("Run actions", type="primary", width="stretch", disabled=blocked):
            steps: list[dict] = []
            if fill_label:
                steps.append({"fill": {"label": fill_label, "text": fill_text}})
            if click_label:
                steps.append({"click": click_label})
            steps.append({"wait_ms": 2500})
            with st.spinner("Driving the app…"):
                out = run(core.browse_app(slug, steps))

    if out is not None:
        st.markdown('<div class="result">', unsafe_allow_html=True)
        if out.get("error"):
            st.markdown(f'<p class="bad">✖ {esc(out["error"])}</p>', unsafe_allow_html=True)
            if out.get("buttons_on_page"):
                st.caption("Buttons on the page: " + ", ".join(out["buttons_on_page"]))
        elif out.get("hint"):
            st.markdown(f'<p class="bad">{esc(state_bits(out.get("state"))[1])} — {esc(out["hint"])}</p>',
                        unsafe_allow_html=True)
        else:
            done = ", ".join(out.get("performed", [])) if out.get("performed") else None
            summary = done or f'{state_bits(out.get("state"))[1]}' + (
                f' in {out["seconds"]}s' if out.get("seconds") else "")
            st.markdown(f'<p class="ok">✔ {esc(summary)}' +
                        (" · signed in" if out.get("signed_in") else "") + "</p>", unsafe_allow_html=True)
        if out.get("screenshot") and Path(out["screenshot"]).exists():
            st.image(out["screenshot"], width="stretch")
        detail = {k: v for k, v in out.items() if k not in ("text", "screenshot", "buttons_on_page")}
        st.markdown(f"<pre>{esc(json.dumps(detail, indent=1))}</pre>", unsafe_allow_html=True)
        if out.get("text"):
            with st.expander("Page text"):
                st.text(out["text"])
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    '<div class="shell"><p class="note">Wake, Screenshot, Browse and the deep status check drive a real '
    "browser, so this page runs on your own machine — Streamlit Community Cloud cannot run one. Logins come "
    "from mcp/credentials.json, which stays out of the repository.</p></div>",
    unsafe_allow_html=True,
)
