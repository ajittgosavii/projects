"""Project portfolio: every application in github.com/ajittgosavii plus local builds."""

import html
import json
from pathlib import Path

import streamlit as st

DATA_FILE = Path(__file__).parent / "projects.json"
SOURCES = {"github": "GitHub repositories", "local": "Local builds (not on GitHub)"}

st.set_page_config(page_title="Application Portfolio", page_icon="🗂️", layout="wide")


@st.cache_data
def load_projects() -> list[dict]:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def render_table(rows: list[dict]) -> None:
    body = []
    for r in rows:
        title = html.escape(r["title"])
        if r.get("repo"):
            title = f'<a href="https://github.com/ajittgosavii/{html.escape(r["repo"])}" target="_blank">{title}</a>'
        body.append(
            f'<tr><td class="sno">{r["sno"]}</td><td class="title">{title}</td>'
            f'<td>{html.escape(r["description"])}</td></tr>'
        )
    st.markdown(
        '<table class="portfolio"><thead><tr><th>S.No</th><th>Application Title</th>'
        f'<th>Description</th></tr></thead><tbody>{"".join(body)}</tbody></table>',
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <style>
      table.portfolio { width: 100%; border-collapse: collapse; font-size: 0.95rem; }
      table.portfolio th { text-align: left; padding: 0.6rem 0.75rem;
        border-bottom: 2px solid rgba(128,128,128,0.45); white-space: nowrap; }
      table.portfolio td { padding: 0.55rem 0.75rem; vertical-align: top;
        border-bottom: 1px solid rgba(128,128,128,0.2); line-height: 1.45; }
      table.portfolio td.sno { width: 4rem; text-align: right; font-variant-numeric: tabular-nums;
        color: rgba(128,128,128,0.95); }
      table.portfolio td.title { width: 26%; font-weight: 600; }
      table.portfolio a { text-decoration: none; }
    </style>
    """,
    unsafe_allow_html=True,
)

projects = load_projects()

st.title("Application Portfolio")
st.caption(
    "Every application in [github.com/ajittgosavii](https://github.com/ajittgosavii), "
    "plus local builds. Titles link to the GitHub repository where there is one."
)

counts = {k: sum(p["source"] == k for p in projects) for k in SOURCES}
c1, c2, c3 = st.columns(3)
c1.metric("Applications", len(projects))
c2.metric("On GitHub", counts["github"])
c3.metric("Local builds", counts["local"])

query = st.text_input("Search", placeholder="Filter by title or description, e.g. FinOps, RDS, Terraform")
if query:
    q = query.lower()
    projects = [p for p in projects if q in p["title"].lower() or q in p["description"].lower()]
    st.caption(f"{len(projects)} match{'es' if len(projects) != 1 else ''}")

for key, heading in SOURCES.items():
    rows = [p for p in projects if p["source"] == key]
    if rows:
        st.subheader(heading)
        render_table(rows)
