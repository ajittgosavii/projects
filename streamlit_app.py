"""ECHO AI Lab – Calgary: the application portfolio, with pillar filters, a portfolio-mix bar and pagination."""

import html
import json
import math
from pathlib import Path

import streamlit as st

import auth

DATA_FILE = Path(__file__).parent / "projects.json"
GITHUB = "https://github.com/ajittgosavii/"
PAGE_SIZES = (10, 20, 50)
ALL_CATEGORIES = "All categories"
# Infosys Hexagon pillar -> categorical colour: the validated default palette's first six slots, in its fixed
# order (the order is what keeps neighbours distinguishable under colour-blindness). Text never wears these.
PILLARS = {
    "AI Strategy & Engineering": "#2a78d6",
    "Data for AI": "#eb6834",
    "Process AI": "#1baf7a",
    "Agentic Legacy Modernization": "#eda100",
    "Physical AI": "#e87ba4",
    "AI Trust": "#008300",
}
SORTS = {
    "Portfolio order": lambda r: r["sno"],
    "Highest modelled savings": lambda r: (-r["savings_usd"], r["sno"]),
    "Title A–Z": lambda r: r["title"].lower(),
    "Infosys Hexagon pillar": lambda r: (list(PILLARS).index(r["hexagon"]), r["sno"]),
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


def money(usd: float) -> str:
    return f"&#36;{usd / 1e6:.2f}M" if usd >= 1e6 else f"&#36;{usd / 1000:,.0f}K"


def pillar(name: str) -> str:
    return f'<span class="pillar" style="--c:{PILLARS[name]}"><span class="hx"></span>{esc(name)}</span>'


def mix_band(projects: list[dict], selected: list[str]) -> str:
    """Part-to-whole bar of the whole portfolio by pillar; pillars outside the filter are dimmed, never repainted."""
    total, saved = len(projects), sum(p["savings_usd"] for p in projects)
    segs, keys = [], []
    for k, (name, colour) in enumerate(PILLARS.items()):
        apps = [p for p in projects if p["hexagon"] == name]
        n, usd = len(apps), sum(p["savings_usd"] for p in apps)
        dim = " dim" if selected and name not in selected else ""
        detail = f"{n} app{'s' if n != 1 else ''}, ~{money(usd)} a year"
        segs.append(f'<div class="seg{dim}" style="--c:{colour};--n:{n};--k:{k}" tabindex="0">'
                    f'<span class="tip"><b>{esc(name)}</b><br>{detail} ({n / total:.0%})</span></div>')
        keys.append(f'<div class="k{dim}">{pillar(name)}<span class="v">{detail}</span></div>')
    return (f'<div class="mix"><div class="mix-head"><span class="mix-title">Portfolio by Infosys Hexagon pillar</span>'
            f'<span class="mix-total">{total} applications, ~{money(saved)} a year modelled</span></div>'
            f'<div class="mixbar" role="img" aria-label="Applications by Infosys Hexagon pillar">{"".join(segs)}</div>'
            f'<div class="mixkey">{"".join(keys)}</div></div>')


def row_html(r: dict, i: int, max_usd: float) -> str:
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
        "benefit": (f'{esc(r["benefit"])}<div class="save">Est. ~{money(r["savings_usd"])} a year</div>'
                    f'<div class="sbar" title="Relative to the largest modelled saving">'
                    f'<span style="width:{100 * r["savings_usd"] / max_usd:.1f}%"></span></div>'
                    f'<div class="basis">{esc(r["savings_basis"])}</div>'),
    }
    tds = "".join(f'<td class="{c}" data-label="{h}">{cells[c]}</td>' for h, c, _ in COLUMNS)
    return f'<tr style="--c:{PILLARS[r["hexagon"]]};--i:{i}">{tds}</tr>'


pill_markers = "\n".join(
    f'.st-key-f_pillar button:nth-of-type({n}) p::before {{ background: {c}; }}'
    for n, c in enumerate(PILLARS.values(), 1)
)
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

      .pillar { display: inline-flex; align-items: baseline; gap: 0.45rem; color: var(--ink); font-weight: 600; }
      .hx { flex: none; width: 0.7rem; height: 0.8rem; background: var(--c); transform: translateY(0.08rem);
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
      .pagehead { font-family: var(--body); color: var(--ink); margin-bottom: 1.2rem; }
      .pagehead .name { font-family: var(--cond); font-weight: 600; font-size: 2.1rem; line-height: 1.1;
                        letter-spacing: -0.01em; }
      .pagehead .lede { color: var(--slate); font-size: 0.98rem; line-height: 1.55; margin: 0.4rem 0 0; max-width: 46rem; }

      /* portfolio mix: one part-to-whole bar, 2px surface gaps, 4px rounded outer ends */
      .mix { font-family: var(--body); background: #fff; border: 1px solid var(--rule); border-radius: 6px;
             padding: 1rem 1.15rem 1.05rem; margin-bottom: 1.1rem; }
      .mix-head { display: flex; flex-wrap: wrap; gap: 0.25rem 1rem; justify-content: space-between;
                  align-items: baseline; margin-bottom: 0.75rem; }
      .mix-title { font-family: var(--cond); font-weight: 600; font-size: 1rem; color: var(--ink); }
      .mix-total { font-size: 0.82rem; color: var(--slate); }
      .mixbar { display: flex; gap: 2px; height: 14px; }
      .seg { position: relative; flex: var(--n) 1 0; min-width: 6px; background: var(--c); outline: none;
             transform-origin: left center; animation: grow 0.8s cubic-bezier(0.2, 0.7, 0.2, 1) both;
             animation-delay: calc(var(--k) * 70ms); transition: opacity 0.2s ease; }
      .seg:first-child { border-radius: 4px 0 0 4px; }
      .seg:last-child { border-radius: 0 4px 4px 0; }
      .seg::after { content: ""; position: absolute; inset: -8px 0; }  /* hit target bigger than the mark */
      .seg.dim, .k.dim { opacity: 0.25; }
      .seg .tip { display: none; position: absolute; z-index: 5; bottom: calc(100% + 10px); left: 50%;
                  transform: translateX(-50%); background: var(--ink); color: #fff; font-size: 0.78rem;
                  line-height: 1.45; padding: 0.4rem 0.6rem; border-radius: 4px; white-space: nowrap;
                  pointer-events: none; }
      .seg:hover .tip, .seg:focus-visible .tip { display: block; }
      .seg:last-child .tip { left: auto; right: 0; transform: none; }
      .seg:focus-visible { box-shadow: 0 0 0 2px #fff, 0 0 0 4px var(--link); }
      .mixkey { display: grid; grid-template-columns: repeat(auto-fill, minmax(13rem, 1fr)); gap: 0.7rem 1.5rem;
                margin-top: 0.95rem; }
      .mixkey .k { font-size: 0.84rem; transition: opacity 0.2s ease; }
      .mixkey .v { display: block; color: var(--slate); font-size: 0.8rem; margin: 0.1rem 0 0 1.15rem; }
      @keyframes grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }

      /* filters */
      .st-key-filters { margin-bottom: 0.4rem; }
      .st-key-clear button p { white-space: nowrap; }
      .st-key-filters label p { font-family: var(--cond); font-weight: 600; font-size: 0.84rem; color: #3E4859; }
      .st-key-f_pillar button p::before { content: ""; display: inline-block; width: 0.62rem; height: 0.7rem;
        margin-right: 0.4rem; transform: translateY(0.05rem);
        clip-path: polygon(50% 0, 100% 25%, 100% 75%, 50% 100%, 0 75%, 0 25%); }
      PILL_MARKERS

      .range { font-family: var(--body); color: var(--slate); font-size: 0.875rem; margin: 0.4rem 0 0.55rem; }
      .range b { color: var(--ink); font-weight: 600; }
      .empty { font-family: var(--body); color: var(--slate); background: #fff; border: 1px dashed var(--rule);
               border-radius: 6px; padding: 2rem; text-align: center; }
      .wrap { border: 1px solid var(--rule); border-radius: 6px; background: #fff; overflow: hidden; }
      table.portfolio { width: 100%; table-layout: fixed; border-collapse: collapse; font-family: var(--body);
                        font-size: 0.85rem; color: var(--ink); }
      table.portfolio th { font-family: var(--cond); font-weight: 600; font-size: 0.84rem; color: #3E4859;
                           text-align: left; background: var(--head); padding: 0.7rem 0.75rem;
                           border-bottom: 1px solid var(--rule); }
      table.portfolio th:first-child { white-space: nowrap; }
      table.portfolio td { padding: 0.8rem 0.75rem; vertical-align: top; line-height: 1.5;
                           border-bottom: 1px solid var(--rule-soft); overflow-wrap: break-word;
                           transition: background 0.15s ease; }
      table.portfolio tbody tr { animation: rowin 0.45s cubic-bezier(0.2, 0.7, 0.2, 1) both;
                                 animation-delay: calc(var(--i) * 35ms); }
      @keyframes rowin { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
      table.portfolio tbody tr:last-child td { border-bottom: 0; }
      table.portfolio tbody tr:hover td { background: #F6F8FC; }
      table.portfolio tbody tr:hover td:first-child { box-shadow: inset 3px 0 0 var(--c); }
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
      .sbar { height: 4px; max-width: 9rem; margin: 0.35rem 0 0.25rem; background: var(--rule-soft); border-radius: 2px;
              overflow: hidden; }
      .sbar span { display: block; height: 100%; min-width: 3px; background: #2a78d6; border-radius: 0 2px 2px 0;
                   transform-origin: left center; animation: grow 0.7s cubic-bezier(0.2, 0.7, 0.2, 1) both;
                   animation-delay: calc(var(--i) * 35ms + 180ms); }
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
        table.portfolio tbody tr:hover td:first-child { box-shadow: none; }
      }
      @media (prefers-reduced-motion: reduce) {
        .seg, .sbar span, table.portfolio tbody tr { animation: none; }
      }

      .method { font-family: var(--body); color: var(--muted); font-size: 0.8rem; line-height: 1.55;
                margin-top: 1.5rem; padding-top: 0.9rem; border-top: 1px solid var(--rule); }
      .method p { margin: 0 0 0.35rem; max-width: 62rem; }
    </style>
    """.replace("PILL_MARKERS", pill_markers),
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
max_usd = max(p["savings_usd"] for p in projects)
categories = sorted({p["category"] for p in projects})

# --- filter + pagination state; session state drives it, the URL mirrors the page so it can be shared ---
st.session_state.setdefault("size", PAGE_SIZES[0])
st.session_state.setdefault("f_pillar", [])
st.session_state.setdefault("f_cat", ALL_CATEGORIES)
st.session_state.setdefault("f_sort", "Portfolio order")
if "page" not in st.session_state:
    try:
        st.session_state.page = int(st.query_params.get("page", 1))
    except ValueError:
        st.session_state.page = 1


def reset_page() -> None:
    st.session_state.page = 1


def clear_filters() -> None:
    st.session_state.f_pillar, st.session_state.f_cat = [], ALL_CATEGORIES
    st.session_state.f_sort, st.session_state.page = "Portfolio order", 1


def go_to(p: int) -> None:
    st.session_state.page = p


def on_pick() -> None:
    if st.session_state.page_seg:  # clicking the selected page again deselects it; keep the page then
        st.session_state.page = st.session_state.page_seg


selected = st.session_state.f_pillar or []
shown = [p for p in projects
         if (not selected or p["hexagon"] in selected)
         and st.session_state.f_cat in (ALL_CATEGORIES, p["category"])]
shown.sort(key=SORTS[st.session_state.f_sort])
filtered = len(shown) != total or st.session_state.f_sort != "Portfolio order"

pages = max(1, math.ceil(len(shown) / st.session_state.size))
st.session_state.page = min(max(1, st.session_state.page), pages)
page = st.session_state.page
st.session_state.page_seg = page  # set before the widget exists, so the control shows the current page
st.query_params["page"] = str(page)

with st.container(key="content"):
    st.markdown(
        '<div class="pagehead"><div class="name">Application Portfolio</div>'
        f'<p class="lede">{total} AI applications across cloud, data, migration and security, each with its '
        "Infosys Hexagon pillar, technology stack and business case. Titles open the GitHub repository.</p></div>"
        + mix_band(projects, selected),
        unsafe_allow_html=True,
    )

    with st.container(key="filters"):
        pill_col, cat_col, sort_col, clear_col = st.columns([5.2, 2, 2, 1.35], vertical_alignment="bottom")
        pill_col.pills("Infosys Hexagon", list(PILLARS), selection_mode="multi", key="f_pillar", on_change=reset_page)
        cat_col.selectbox("Category", [ALL_CATEGORIES, *categories], key="f_cat", on_change=reset_page)
        sort_col.selectbox("Sort by", list(SORTS), key="f_sort", on_change=reset_page)
        clear_col.button("Clear filters", key="clear", on_click=clear_filters, disabled=not filtered, width="stretch")

    start = (page - 1) * st.session_state.size
    rows = shown[start:start + st.session_state.size]
    if rows:
        of = f"<b>{len(shown)}</b> of <b>{total}</b>" if len(shown) != total else f"<b>{total}</b>"
        colgroup = "".join(f'<col style="width:{w}">' for _, _, w in COLUMNS)
        heads = "".join(f"<th>{h}</th>" for h, _, _ in COLUMNS)
        body = "".join(row_html(r, i, max_usd) for i, r in enumerate(rows))
        st.markdown(
            f'<div class="range">Showing <b>{start + 1}–{start + len(rows)}</b> of {of} applications</div>'
            f'<div class="wrap"><table class="portfolio"><colgroup>{colgroup}</colgroup>'
            f"<thead><tr>{heads}</tr></thead><tbody>{body}</tbody></table></div>",
            unsafe_allow_html=True,
        )
        prev_col, pages_col, next_col, _, size_col = st.columns([0.9, 3.4, 0.9, 3.2, 1.4],
                                                                vertical_alignment="center")
        prev_col.button("Previous", key="prev", on_click=go_to, args=(page - 1,), disabled=page <= 1,
                        width="stretch")
        pages_col.segmented_control("Page", list(range(1, pages + 1)), key="page_seg", on_change=on_pick,
                                    label_visibility="collapsed")
        next_col.button("Next", key="next", on_click=go_to, args=(page + 1,), disabled=page >= pages,
                        width="stretch")
        size_col.selectbox("Rows per page", PAGE_SIZES, key="size", on_change=reset_page,
                           label_visibility="collapsed", format_func=lambda n: f"{n} per page")
    else:
        st.markdown('<div class="empty">No applications match these filters. Clear the filters to see all '
                    f"{total}.</div>", unsafe_allow_html=True)

    st.markdown(
        '<div class="method"><p>Business Benefits are conservative, modelled estimates of potential annual savings '
        "for a mid-size enterprise, not measured results. Labour savings are hours saved per year at a &#36;75/hr "
        "blended rate; FinOps savings are 2–3% of an assumed &#36;1M/yr cloud bill. Each row shows its basis; the "
        "bar under each figure compares it with the largest modelled saving.</p>"
        f"<p>{auth.LAB_NAME}. {auth.COLLAB}.</p></div>",
        unsafe_allow_html=True,
    )
