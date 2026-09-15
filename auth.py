"""Sign-in gate and the ECHO AI Lab login page.

Accounts live in the app's secrets, never in the repo:

    [auth.users]
    alice = "pbkdf2_sha256$240000$<salt-hex>$<digest-hex>"

Create a hash with:  python -c "import auth; print(auth.hash_password('the-password'))"
"""

import hashlib
import hmac
import secrets
import time

import streamlit as st

LAB_NAME = "ECHO AI Lab – Calgary"
COLLAB = "In Collaboration with CIS CLD"
MAX_ATTEMPTS, LOCKOUT_SECONDS = 5, 60
ITERATIONS = 240_000
# the Hexagon pillars as they read on the dark brand panel
PILLARS_ON_DARK = {
    "AI Strategy & Engineering": "#8DB8FF",
    "Data for AI": "#63D3DC",
    "Process AI": "#BBA3FF",
    "Agentic Legacy Modernization": "#F2B866",
    "Physical AI": "#FF93A5",
    "AI Trust": "#86D98F",
}


def hash_password(password: str, salt_hex: str | None = None, iterations: int = ITERATIONS) -> str:
    salt_hex = salt_hex or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), iterations)
    return f"pbkdf2_sha256${iterations}${salt_hex}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt_hex, digest = stored.split("$")
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
    except ValueError:
        return False
    return hmac.compare_digest(candidate.hex(), digest)


# checked against when the username is unknown, so a wrong username takes as long as a wrong password
_DUMMY_HASH = hash_password("unused", "00" * 16)


def _users() -> dict[str, str]:
    try:
        return {name: str(h) for name, h in st.secrets["auth"]["users"].items()}
    except Exception:  # no secrets file, or no [auth.users] section
        return {}


def logo_svg(size: int, uid: str) -> str:
    """Hexagon with echo waves travelling out from a point; uid keeps gradient ids unique per page."""
    arcs = "".join(
        f'<path d="M{22 + 0.643 * r:.1f} {32 - 0.766 * r:.1f}A{r} {r} 0 0 1 {22 + 0.643 * r:.1f} {32 + 0.766 * r:.1f}"'
        f' stroke-opacity="{op}"/>'
        for r, op in ((9, 1), (15, 0.72), (21, 0.45))
    )
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 64 64" role="img" aria-label="ECHO AI Lab logo" '
        f'xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="g{uid}" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="#7FD6F5"/><stop offset="1" stop-color="#2E6FD8"/></linearGradient></defs>'
        f'<polygon points="32,3 57,17.5 57,46.5 32,61 7,46.5 7,17.5" fill="none" stroke="url(#g{uid})" '
        f'stroke-width="3.5" stroke-linejoin="round"/><circle cx="22" cy="32" r="4.5" fill="url(#g{uid})"/>'
        f'<g fill="none" stroke="url(#g{uid})" stroke-width="3.2" stroke-linecap="round">{arcs}</g></svg>'
    )


_LOGIN_CSS = """
<style>
  [data-testid="stHeader"] { display: none; }
  .block-container { max-width: none; padding: 0 !important; }
  .st-key-login_shell [data-testid="stHorizontalBlock"] { gap: 0; align-items: stretch !important; }
  .st-key-login_shell [data-testid="stColumn"]:nth-child(2) {
    align-self: stretch; min-height: 100vh; box-sizing: border-box; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    background: #fff; border-left: 1px solid var(--rule); padding: 3rem 2.5rem; }
  .st-key-login_shell [data-testid="stColumn"]:nth-child(2) > div {
    width: 100%; max-width: 23rem; flex: 0 0 auto !important; height: auto !important; }

  .brand { position: relative; overflow: hidden; min-height: 100vh; box-sizing: border-box; color: #fff;
           display: flex; flex-direction: column; justify-content: space-between; padding: 2.5rem 3.5rem 0;
           font-family: var(--body);
           background: radial-gradient(85% 70% at 88% 48%, #1C4088 0%, #11295A 42%, #0A1733 100%); }
  .brand > * { position: relative; z-index: 2; }
  .brand .hero { max-width: 33rem; padding: 3rem 0; }
  .brand .lab { font-family: var(--cond); font-weight: 600; font-size: clamp(2.3rem, 3.5vw, 3.3rem);
                line-height: 1.04; letter-spacing: -0.015em; }
  .brand .pitch { color: #BFCAE0; font-size: 1.05rem; line-height: 1.6; margin: 1.1rem 0 2rem; max-width: 30rem; }
  .brand .pillars { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.6rem 1.5rem;
                    font-size: 0.86rem; max-width: 30rem; }
  .brand .foot { color: #A9B8D2; font-size: 0.85rem; padding: 0 0 8.5rem; }
  .brand .echo { position: absolute; z-index: 1; right: -10rem; top: 50%; width: 36rem; height: 36rem;
                 transform: translateY(-50%); pointer-events: none; }
  .brand .echo > svg { width: 100%; height: 100%; opacity: 0.1; }
  .brand .rings span { position: absolute; left: 50%; top: 50%; width: 18rem; height: 18rem; margin: -9rem 0 0 -9rem;
                       border: 1.5px solid rgba(127, 214, 245, 0.42); border-radius: 50%; opacity: 0;
                       animation: echo 7.5s cubic-bezier(0.2, 0.6, 0.3, 1) infinite; }
  .brand .rings span:nth-child(2) { animation-delay: 2.5s; }
  .brand .rings span:nth-child(3) { animation-delay: 5s; }
  @keyframes echo { 0% { transform: scale(0.4); opacity: 0.8; } 100% { transform: scale(2.5); opacity: 0; } }
  .brand .ridge { position: absolute; z-index: 1; left: 0; bottom: 0; width: 100%; height: 150px; }

  .signin .title { font-family: var(--cond); font-weight: 600; font-size: 1.9rem; color: var(--ink); }
  .signin p { font-family: var(--body); color: var(--slate); line-height: 1.55; margin: 0.35rem 0 1.4rem; }
  .signin-foot { font-family: var(--body); color: var(--muted); font-size: 0.8rem; line-height: 1.5; margin-top: 1rem; }
  .st-key-login_shell [data-testid="stFormSubmitButton"] button { min-height: 2.8rem; font-weight: 600; }

  @media (prefers-reduced-motion: reduce) { .brand .rings span { animation: none; } }
  @media (max-width: 640px) {
    .brand { min-height: 0; padding: 1.75rem 1.5rem 0; }
    .brand .hero { padding: 2rem 0 1.5rem; }
    .brand .pillars { grid-template-columns: 1fr; }
    .brand .foot { padding-bottom: 7rem; }
    .brand .echo { right: -16rem; opacity: 0.7; }
    .st-key-login_shell [data-testid="stColumn"]:nth-child(2) { border-left: 0; min-height: 0; padding: 2rem 1.5rem 3rem; }
  }
</style>
"""

_RIDGE = (
    '<svg class="ridge" viewBox="0 0 600 140" preserveAspectRatio="none" aria-hidden="true">'
    '<path d="M0 140V92l48-18 38 12 52-40 40 26 46-44 52 46 40-24 44 30 50-52 46 36 42-14 52 20 50-8V140z" '
    'fill="rgba(127,214,245,0.07)"/>'
    '<path d="M0 140v-26l70-22 54 14 60-30 58 28 48-18 66 24 56-30 62 22 54-12 72 20v30z" fill="#081329"/>'
    '<path d="M0 92l48-18 38 12 52-40 40 26 46-44 52 46 40-24 44 30 50-52 46 36 42-14 52 20 50-8" fill="none" '
    'stroke="rgba(127,214,245,0.35)" stroke-width="1.2"/></svg>'
)


def _brand_panel() -> str:
    pillars = "".join(
        f'<span class="pillar" style="--c:{c}"><span class="hx"></span>{name}</span>'
        for name, c in PILLARS_ON_DARK.items()
    )
    return (
        f'<div class="brand"><div class="mark">{logo_svg(44, "login")}</div>'
        f'<div class="hero"><div class="lab">{LAB_NAME}</div>'
        '<p class="pitch">The catalogue of AI applications built by the lab across cloud, data, migration and '
        'security, each mapped to its Infosys Hexagon pillar and business case.</p>'
        f'<div class="pillars">{pillars}</div></div>'
        f'<div class="foot">{COLLAB}</div>'
        f'<div class="echo" aria-hidden="true"><div class="rings"><span></span><span></span><span></span></div>'
        f'{logo_svg(576, "echo")}</div>{_RIDGE}</div>'
    )


def _attempt(users: dict[str, str], username: str, password: str) -> None:
    now = time.time()
    locked_until = st.session_state.get("auth_locked_until", 0.0)
    if now < locked_until:
        st.error(f"Too many attempts. Try again in {int(locked_until - now) + 1} seconds.")
        return
    stored = users.get(username)
    if verify_password(password, stored or _DUMMY_HASH) and stored is not None:
        st.session_state.auth_user = username
        st.session_state.auth_fails = 0
        st.rerun()
    fails = st.session_state.get("auth_fails", 0) + 1
    if fails >= MAX_ATTEMPTS:
        st.session_state.auth_locked_until, fails = now + LOCKOUT_SECONDS, 0
    st.session_state.auth_fails = fails
    st.error("Incorrect username or password.")


def require_login() -> bool:
    """True once the viewer has signed in; otherwise draws the login page and returns False."""
    if st.session_state.get("auth_user"):
        return True
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)
    users = _users()
    with st.container(key="login_shell"):
        brand, form = st.columns([1.45, 1])  # stretch, so the white sign-in panel runs full height
        brand.markdown(_brand_panel(), unsafe_allow_html=True)
        with form:
            st.markdown('<div class="signin"><div class="title">Sign in</div>'
                        "<p>Use the username and password from your lab administrator.</p></div>",
                        unsafe_allow_html=True)
            if not users:
                st.warning("Sign-in isn't set up yet. Add an [auth.users] section to this app's secrets.")
            with st.form("login", border=False):
                username = st.text_input("Username", autocomplete="username")
                password = st.text_input("Password", type="password", autocomplete="current-password")
                submitted = st.form_submit_button("Sign in", type="primary", width="stretch", disabled=not users)
            if submitted:
                _attempt(users, username.strip(), password)
            st.markdown('<div class="signin-foot">Access is limited to ECHO AI Lab members.</div>',
                        unsafe_allow_html=True)
    return False


def current_user() -> str:
    return st.session_state.get("auth_user", "")


def sign_out() -> None:
    st.session_state.pop("auth_user", None)
