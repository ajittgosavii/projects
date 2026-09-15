"""ECHO AI Lab – Calgary: the application portfolio, paginated, with pillar, stack, drivers and modelled benefits."""

import html
import json
import math
from pathlib import Path

import streamlit as st

import auth

DATA_FILE = Path(__file__).parent / "projects.json"
GITHUB = "https://github.com/ajittgosavii/"
PAGE_SIZES = (10, 20, 50)
# Infosys Hexagon pillar -> its colour (all pass WCAG AA as text on white)
PILLARS = {
    "AI Strategy & Engineering": "#1A4E9C",
    "Data for AI": "#0B636B",
    "Process AI": "#5A3DA3",
    "Agentic Legacy Modernization": "#8F4F00",
    "Physical AI": "#9E2439",
    "AI Trust": "#23632A",
}
# (header, css class, column width) — widths add up to 100% so the table always fits the page
COLUMNS = [
    ("S.No", "sno", "4.4%"), ("Application Title", "title", "13%"), ("Description", "desc", "23%"),
    ("Category", "cat", "8.6%"), ("Infosys Hexagon", "hex", "10.6%"), ("Technology Stack", "stack", "13.6%"),
    ("Business Drivers", "drivers", "10%"), ("Business Benefits (est.)", "benefit", "16.8%"),
]

st.set_page_config(page_title="ECHO AI Lab – Calgary", page_icon="🔷", layout="wide")


@st.cache_data
def load_projects(mtime: float) -> list[dict]:
    """mtime is part of the cache key, so a new projects.json is picked up instead of a stale cached copy."""
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def esc(value) -> str:
    # st.markdown reads "$...$" as LaTeX, so dollar signs are written as an entity
    return html.escape(str(value)).replace("$", "&#36;")


def pillar(name: str) -> str:
    return f'<span class="pillar" style="--c:{PILLARS[name]}"><span class="hx"></span>{esc(name)}</span>'


def row_html(r: dict) -> str:
    title = esc(r["title"])
    if r.get("repo"):
        title = f'<a href="{GITHUB}{esc(r["repo"])}" target="_blank" rel="noopener">{title}</a>'
    if r.get("variants"):
        links = ", ".join(f'<a href="{GITHUB}{esc(v)}" target="_blank" rel="noopener">{esc(v)}</a>'
                          for v in r["variants"])
        title += f'<div class="variants">Also built as {links}</div>'
    cells = {
        "sno": str(r["sno"]),
        "title": title,
        "desc": esc(r["description"]),
        "cat": esc(r["category"]),
        "hex": pillar(r["hexagon"]),
        "stack": "".join(f'<span class="chip">{esc(s)}</span>' for s in r["stack"]),
        "drivers": "".join(f"<div>{esc(d.strip())}</div>" for d in r["drivers"].split("·")),
        "benefit": (f'{esc(r["benefit"])}<div class="save">Est. ~&#36;{r["savings_usd"] / 1000:,.0f}K a year</div>'
                    f'<div class="basis">{esc(r["savings_basis"])}</div>'),
    }
    return "<tr>" + "".join(f'<td class="{c}" data-label="{h}">{cells[c]}</td>' for h, c, _ in COLUMNS) + "</tr>"


st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@500;600&display=swap');
      :root { --ink:#14213D; --slate:#5B6475; --muted:#6A7386; --rule:#DDE2EA; --rule-soft:#E8ECF2;
              --canvas:#F7F8FA; --head:#EEF1F5; --link:#1F5FBF; --navy:#0F2248; --gutter:2.5rem;
              --body:'IBM Plex Sans', 'Segoe UI', system-ui, sans-serif;
              --cond:'IBM Plex Sans Condensed', 'Arial Narrow', 'Segoe UI', sans-serif; }
      [data-testid="stHeader"] { display: none; }
      footer { visibility: hidden; }
      /* the blocks that only carry <style> would otherwise each take a layout gap at the top */
      [data-testid="stElementContainer"]:has(style) { display: none; }
      .block-container { max-width: none; padding: 0 var(--gutter) 3rem !important; }

      .pillar { display: inline-flex; align-items: baseline; gap: 0.42rem; color: var(--c); font-weight: 600; }
      .hx { flex: none; width: 0.68rem; height: 0.78rem; background: var(--c); transform: translateY(0.08rem);
            clip-path: polygon(50% 0, 100% 25%, 100% 75%, 50% 100%, 0 75%, 0 25%); }

      /* app bar: full-bleed navy band across the top */
      .st-key-appbar { background: var(--navy); width: calc(100% + 2 * var(--gutter)) !important;
                       max-width: none !important; margin: 0 calc(-1 * var(--gutter)) 2rem !important;
                       padding: 0.7rem var(--gutter); box-sizing: border-box; }
      .st-key-appbar button p { white-space: nowrap; }
      .st-key-appbar [data-testid="stHorizontalBlock"] { max-width: 1560px; margin: 0 auto; }
      .lockup { display: flex; align-items: center; gap: 0.75rem; font-family: var(--body); }
      .lockup .lab { font-family: var(--cond); font-weight: 600; font-size: 1.12rem; color: #fff; line-height: 1.2; }
      .lockup .collab { font-size: 0.78rem; color: #9FB0CC; }
      .who { font-family: var(--body); text-align: right; font-size: 0.85rem; color: #BFCAE0; }
      .who b { color: #fff; font-weight: 600; }
      .st-key-appbar button { background: transparent; color: #fff; border: 1px solid rgba(255,255,255,0.35); }
      .st-key-appbar button:hover, .st-key-appbar button:focus-visible {
        background: rgba(255,255,255,0.08); color: #fff; border-color: #fff; }

      .st-key-content { max-width: 1560px; margin: 0 auto; width: 100%; }
      .pagehead { font-family: var(--body); color: var(--ink); display: flex; flex-wrap: wrap; gap: 1rem 3rem;
                  align-items: flex-end; justify-content: space-between; padding-bottom: 1.2rem;
                  border-bottom: 1px solid var(--rule); margin-bottom: 1.1rem; }
      .pagehead .name { font-family: var(--cond); font-weight: 600; font-size: 2.1rem; line-height: 1.1;
                        letter-spacing: -0.01em; }
      .pagehead .lede { color: var(--slate); font-size: 0.98rem; line-height: 1.55; margin: 0.4rem 0 0; max-width: 44rem; }
      .legend { display: flex; flex-wrap: wrap; gap: 0.45rem 1.2rem; align-items: baseline; font-size: 0.82rem;
                max-width: 40rem; }
      .legend .key { color: var(--muted); }

      .range { font-family: var(--body); color: var(--slate); font-size: 0.875rem; margin: 0 0 0.55rem; }
      .range b { color: var(--ink); font-weight: 600; }
      .wrap { border: 1px solid var(--rule); border-radius: 6px; background: #fff; overflow: hidden; }
      table.portfolio { width: 100%; table-layout: fixed; border-collapse: collapse; font-family: var(--body);
                        font-size: 0.85rem; color: var(--ink); }
      table.portfolio th { font-family: var(--cond); font-weight: 600; font-size: 0.84rem; color: #3E4859;
                           text-align: left; background: var(--head); padding: 0.7rem 0.75rem;
                           border-bottom: 1px solid var(--rule); }
      table.portfolio th:first-child { white-space: nowrap; }
      table.portfolio td { padding: 0.8rem 0.75rem; vertical-align: top; line-height: 1.5;
                           border-bottom: 1px solid var(--rule-soft); overflow-wrap: break-word; }
      table.portfolio tbody tr:last-child td { border-bottom: 0; }
      table.portfolio tbody tr:hover td { background: #FAFBFD; }
      td.sno { text-align: right; color: var(--muted); font-variant-numeric: tabular-nums; }
      td.title { font-weight: 600; }
      td.title a { color: var(--ink); text-decoration: none; }
      td.title a:hover { color: var(--link); text-decoration: underline; }
      td.desc { color: #2B3548; }
      td.cat, td.drivers { color: var(--slate); }
      td.drivers div + div { margin-top: 0.2rem; }
      .variants { margin-top: 0.3rem; font-weight: 400; font-size: 0.75rem; line-height: 1.5; color: var(--muted); }
      .variants a { color: var(--link); text-decoration: none; }
      .variants a:hover { text-decoration: underline; }
      table.portfolio a:focus-visible { outline: 2px solid var(--link); outline-offset: 2px; border-radius: 2px; }
      .chip { display: inline-block; max-width: 100%; overflow: hidden; text-overflow: ellipsis; vertical-align: top;
              margin: 0 0.25rem 0.3rem 0; padding: 0.05rem 0.42rem; font-size: 0.74rem; color: #3A4458;
              background: var(--canvas); border: 1px solid #D3D9E3; border-radius: 3px; white-space: nowrap; }
      .save { margin-top: 0.4rem; font-weight: 600; font-size: 0.95rem; font-variant-numeric: tabular-nums; }
      .basis { font-size: 0.75rem; color: var(--muted); }

      /* narrower screens: each application becomes a stacked card with field labels */
      @media (max-width: 1100px) {
        table.portfolio, table.portfolio tbody, table.portfolio tr, table.portfolio td { display: block; width: auto; }
        table.portfolio colgroup, table.portfolio thead { display: none; }
        table.portfolio tr { padding: 1rem 1.1rem; border-bottom: 1px solid var(--rule); }
        table.portfolio tbody tr:last-child { border-bottom: 0; }
        table.portfolio td { border: 0; padding: 0.3rem 0; }
        table.portfolio td::before { content: attr(data-label); display: block; font-family: var(--cond);
                                     font-weight: 600; font-size: 0.74rem; color: var(--muted); }
        table.portfolio td.sno, table.portfolio td.title { display: inline-block; font-size: 1rem; }
        table.portfolio td.sno { margin-right: 0.5rem; }
        table.portfolio td.sno::before, table.portfolio td.title::before { content: none; }
        table.portfolio tbody tr:hover td { background: transparent; }
      }

      .method { font-family: var(--body); color: var(--muted); font-size: 0.8rem; line-height: 1.55;
                margin-top: 1.5rem; padding-top: 0.9rem; border-top: 1px solid var(--rule); }
      .method p { margin: 0 0 0.35rem; max-width: 62rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

if not auth.require_login():
    st.stop()

with st.container(key="appbar"):
    brand_col, user_col, out_col = st.columns([6, 2.6, 1.2], vertical_alignment="center")
    brand_col.markdown(
        f'<div class="lockup">{auth.logo_svg(34, "bar")}<div><div class="lab">{auth.LAB_NAME}</div>'
        f'<div class="collab">{auth.COLLAB}</div></div></div>',
        unsafe_allow_html=True,
    )
    user_col.markdown(f'<div class="who">Signed in as <b>{esc(auth.current_user())}</b></div>',
                      unsafe_allow_html=True)
    out_col.button("Sign out", key="signout", on_click=auth.sign_out, width="stretch")

projects = load_projects(DATA_FILE.stat().st_mtime)
total = len(projects)

# --- pagination state: session state drives it, the URL mirrors it so a page can be shared ---
if "size" not in st.session_state:
    st.session_state.size = PAGE_SIZES[0]
pages = math.ceil(total / st.session_state.size)
if "page" not in st.session_state:
    try:
        st.session_state.page = int(st.query_params.get("page", 1))
    except ValueError:
        st.session_state.page = 1
st.session_state.page = min(max(1, st.session_state.page), pages)
page = st.session_state.page
st.session_state.page_seg = page  # set before the widget exists, so the control shows the current page
st.query_params["page"] = str(page)


def go_to(p: int) -> None:
    st.session_state.page = p


def on_pick() -> None:
    if st.session_state.page_seg:  # clicking the selected page again deselects it; keep the page then
        st.session_state.page = st.session_state.page_seg


def on_resize() -> None:
    st.session_state.page = 1


with st.container(key="content"):
    legend = "".join(pillar(p) for p in PILLARS)
    st.markdown(
        f"""
        <div class="pagehead">
          <div><div class="name">Application Portfolio</div>
          <p class="lede">{total} AI applications across cloud, data, migration and security, each with its
          Infosys Hexagon pillar, technology stack and business case. Titles open the GitHub repository.</p></div>
          <div class="legend"><span class="key">Infosys Hexagon</span>{legend}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    start = (page - 1) * st.session_state.size
    rows = projects[start:start + st.session_state.size]
    colgroup = "".join(f'<col style="width:{w}">' for _, _, w in COLUMNS)
    heads = "".join(f"<th>{h}</th>" for h, _, _ in COLUMNS)
    st.markdown(
        f'<div class="range">Showing <b>{start + 1}–{start + len(rows)}</b> of <b>{total}</b> applications</div>'
        f'<div class="wrap"><table class="portfolio"><colgroup>{colgroup}</colgroup>'
        f'<thead><tr>{heads}</tr></thead><tbody>{"".join(row_html(r) for r in rows)}</tbody></table></div>',
        unsafe_allow_html=True,
    )

    prev_col, pages_col, next_col, _, size_col = st.columns([0.9, 3.4, 0.9, 3.2, 1.4], vertical_alignment="center")
    prev_col.button("Previous", key="prev", on_click=go_to, args=(page - 1,), disabled=page <= 1, width="stretch")
    pages_col.segmented_control("Page", list(range(1, pages + 1)), key="page_seg", on_change=on_pick,
                                label_visibility="collapsed")
    next_col.button("Next", key="next", on_click=go_to, args=(page + 1,), disabled=page >= pages, width="stretch")
    size_col.selectbox("Rows per page", PAGE_SIZES, key="size", on_change=on_resize, label_visibility="collapsed",
                       format_func=lambda n: f"{n} per page")

    st.markdown(
        '<div class="method"><p>Business Benefits are conservative, modelled estimates of potential annual savings '
        "for a mid-size enterprise, not measured results. Labour savings are hours saved per year at a &#36;75/hr "
        "blended rate; FinOps savings are 2–3% of an assumed &#36;1M/yr cloud bill. Each row shows its basis.</p>"
        f"<p>{auth.LAB_NAME}. {auth.COLLAB}.</p></div>",
        unsafe_allow_html=True,
    )
