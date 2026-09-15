# Application Portfolio

A paginated Streamlit page listing every application in [github.com/ajittgosavii](https://github.com/ajittgosavii), local builds in `C:\aidemos`, and apps hosted on AWS. Each entry has a serial number, a title, a two-line description, a Category (use case or industry) and its Infosys Hexagon pillar (AI Strategy & Engineering, Data for AI, Process AI, Agentic Legacy Modernization, Physical AI, AI Trust), its Technology Stack (detected from each app's dependency files), Business Drivers, and Business Benefits with a conservative estimated annual saving.

Savings are modelled, not measured: labour savings = hours saved per year × $75/hr blended rate; FinOps savings = 2–3% of an assumed $1M/yr cloud bill. Each row shows its basis. Apps with several builds are listed once, with the other repositories shown as variants.

## Run locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deploy on Streamlit Community Cloud

New app → repository `ajittgosavii/projects`, branch `main`, main file `streamlit_app.py`.

## Sign-in

The page opens on the ECHO AI Lab – Calgary login. Accounts are kept in the app's secrets (Streamlit Cloud → Manage app → Settings → Secrets, or `.streamlit/secrets.toml` locally, which is gitignored), as salted PBKDF2 hashes:

```toml
[auth.users]
"echo-admin" = "pbkdf2_sha256$240000$<salt>$<digest>"
```

Add a user by hashing their password: `python -c "import auth; print(auth.hash_password('their-password'))"`. The login protects the page, not the repo: `projects.json` is readable by anyone who can see this repository.

## Updating the list

All entries are in `projects.json` (`sno`, `title`, `description`, `source` = `github` | `local` | `aws`, `repo`, `where`). Edit that file and push; the page reloads from it.

Not listed: empty or placeholder repos, forks, and private repos.
