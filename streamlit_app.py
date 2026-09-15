"""Project portfolio: every application in github.com/ajittgosavii, local builds, and AWS-hosted apps."""

import html
import json
from pathlib import Path

import streamlit as st

DATA_FILE = Path(__file__).parent / "projects.json"
SOURCES = {
    "github": "GitHub repositories",
    "local": "Local builds in C:\\aidemos (not on GitHub)",
    "aws": "Other applications hosted on AWS",
}

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
        if r.get("variants"):
            links = ", ".join(
                f'<a href="https://github.com/ajittgosavii/{html.escape(v)}" target="_blank">{html.escape(v)}</a>'
                for v in r["variants"]
            )
            title += f'<div class="variants">Variants: {links}</div>'
        where = "".join(f'<span class="badge">{html.escape(w)}</span>' for w in r.get("where", []))
        body.append(
            f'<tr><td class="sno">{r["sno"]}</td><td class="title">{title}</td>'
            f'<td>{html.escape(r["description"])}</td><td class="where">{where}</td></tr>'
        )
    st.markdown(
        '<div class="wrap"><table class="portfolio"><thead><tr><th>S.No</th><th>Application Title</th>'
        f'<th>Description</th><th>Where</th></tr></thead><tbody>{"".join(body)}</tbody></table></div>',
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <style>
      .wrap { overflow-x: auto; }
      table.portfolio { width: 100%; border-collapse: collapse; font-size: 0.95rem; }
      table.portfolio th { text-align: left; padding: 0.6rem 0.75rem;
        border-bottom: 2px solid rgba(128,128,128,0.45); white-space: nowrap; }
      table.portfolio td { padding: 0.55rem 0.75rem; vertical-align: top;
        border-bottom: 1px solid rgba(128,128,128,0.2); line-height: 1.45; }
      table.portfolio td.sno { width: 4rem; text-align: right; font-variant-numeric: tabular-nums;
        color: rgba(128,128,128,0.95); }
      table.portfolio td.title { width: 24%; font-weight: 600; }
      table.portfolio td.where { width: 9rem; }
      table.portfolio a { text-decoration: none; }
      .variants { margin-top: 0.25rem; font-weight: 400; font-size: 0.78rem; line-height: 1.5;
        color: rgba(128,128,128,0.95); }
      .badge { display: inline-block; margin: 0 0.3rem 0.3rem 0; padding: 0.05rem 0.45rem;
        border: 1px solid rgba(128,128,128,0.45); border-radius: 0.6rem; font-size: 0.75rem;
        white-space: nowrap; }
    </style>
    """,
    unsafe_allow_html=True,
)

projects = load_projects()

st.title("Application Portfolio")
st.caption(
    "Every application in [github.com/ajittgosavii](https://github.com/ajittgosavii), local builds, "
    "and apps hosted on AWS. Titles link to the GitHub repository where there is one; "
    "apps with several builds are listed once, with the other repositories shown as variants."
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Applications", len(projects))
c2.metric("On GitHub", sum("GitHub" in p.get("where", []) for p in projects))
c3.metric("In C:\\aidemos", sum("C:\\aidemos" in p.get("where", []) for p in projects))
c4.metric("Hosted on AWS", sum("AWS" in p.get("where", []) for p in projects))

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
