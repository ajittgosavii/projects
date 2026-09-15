# Application Portfolio

A Streamlit page listing every application in [github.com/ajittgosavii](https://github.com/ajittgosavii), plus local builds that aren't on GitHub. Each entry has a serial number, a title, and a two-line description.

## Run locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deploy on Streamlit Community Cloud

New app → repository `ajittgosavii/projects`, branch `main`, main file `streamlit_app.py`.

## Updating the list

All entries are in `projects.json` (`sno`, `title`, `description`, `source` = `github` | `local`, `repo`). Edit that file and push; the page reloads from it.

Not listed: empty or placeholder repos, forks, and private repos.
