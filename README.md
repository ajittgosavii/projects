# Application Portfolio

A Streamlit page listing every application in [github.com/ajittgosavii](https://github.com/ajittgosavii), local builds in `C:\aidemos`, and apps hosted on AWS. Each entry has a serial number, a title, a two-line description, a Category (use case or industry) and its Infosys Hexagon pillar (AI Strategy & Engineering, Data for AI, Process AI, Agentic Legacy Modernization, Physical AI, AI Trust). Apps with several builds are listed once, with the other repositories shown as variants.

## Run locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deploy on Streamlit Community Cloud

New app → repository `ajittgosavii/projects`, branch `main`, main file `streamlit_app.py`.

## Updating the list

All entries are in `projects.json` (`sno`, `title`, `description`, `source` = `github` | `local` | `aws`, `repo`, `where`). Edit that file and push; the page reloads from it.

Not listed: empty or placeholder repos, forks, and private repos.
