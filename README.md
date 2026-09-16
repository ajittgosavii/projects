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

## MCP server

`mcp/server.py` exposes these applications to Claude over MCP (stdio, runs locally):

| Tool | What it does |
|---|---|
| `list_apps` | the catalogue, filtered by pillar, category or free text |
| `get_app` | one application's full entry plus its Streamlit Cloud URL |
| `check_app` | is it running, asleep, private or not deployed |
| `wake_app` | clicks "Yes, get this app back up!" and waits for the app |
| `screenshot_app` | returns a picture of the live app |
| `browse_app` | fills fields and clicks buttons, then reports what the page says |
| `discover_apps` | probes `https://<repo>.streamlit.app` for every catalogue entry and caches what it finds in `mcp/apps.json` |

Setup:

```bash
pip install -r mcp/requirements.txt
python -m playwright install chromium
claude mcp add echo-apps -s user -- python /absolute/path/to/mcp/server.py
```

There is also a local control panel with the same actions, for when you'd rather click than ask Claude:

```bash
streamlit run mcp/ui.py --server.port 8533
```

It lists every discovered app with its state, and runs check, wake, screenshot and browse against the one you pick. Run it locally: those actions drive a real browser, which Streamlit Community Cloud cannot do.

For apps behind a login, add `mcp/credentials.json` (gitignored) so screenshots and browsing can sign in:

```json
{ "echoaiprojects": { "username": "echo-admin", "password": "..." } }
```

Streamlit Community Cloud has no public API, so app URLs are guessed from repo names and verified, and an app's real state (running, asleep, private) is read from the page in a headless browser — HTTP alone can't tell those apart.

## Updating the list

All entries are in `projects.json` (`sno`, `title`, `description`, `source` = `github` | `local` | `aws`, `repo`, `where`). Edit that file and push; the page reloads from it.

Not listed: empty or placeholder repos, forks, and private repos.
