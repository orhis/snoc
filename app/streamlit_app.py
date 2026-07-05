"""
Entry point — szkielet apki FAM. Logowanie (hasło + opcjonalne 2FA) z rate-limit
i timeoutem sesji, potem pusty dashboard. Z tego klonujesz nowy projekt.

Uruchom:  streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import streamlit as st
from fam_auth import bump_activity, check_session_timeout

from app.auth import (
    InvalidCredentials,
    RateLimitExceeded,
    TwoFactorRequired,
    authenticate,
)
from app.db import get_db

st.set_page_config(page_title="SNOC", page_icon="📡", layout="wide")


def _client_ip() -> str:
    # W produkcji za reverse-proxy weź nagłówek X-Forwarded-For (zależnie od setupu).
    return "unknown"


def login_view() -> None:
    st.title("🔐 Logowanie")
    with st.form("login"):
        username = st.text_input("Użytkownik")
        password = st.text_input("Hasło", type="password")
        code = st.text_input("Kod 2FA (jeśli włączone)", max_chars=6)
        submitted = st.form_submit_button("Zaloguj")

    if not submitted:
        return
    try:
        session = authenticate(get_db(), username, password, code=code or None, ip=_client_ip())
    except RateLimitExceeded as e:
        st.error(f"Zbyt wiele prób. Spróbuj po {e.unlock_at:%H:%M:%S} UTC.")
    except TwoFactorRequired:
        st.warning("Podaj kod 2FA z aplikacji uwierzytelniającej.")
    except InvalidCredentials:
        st.error("Nieprawidłowy login lub hasło.")
    else:
        st.session_state["login"] = session
        st.rerun()


def dashboard_view(session) -> None:
    """Nawigacja SNOC (T4): widoki dostają zalogowaną sesję — gate jest jeden, tutaj."""
    from app.views import obserwacje, ustawienia, zdarzenia, zlecenia

    with st.sidebar:
        st.markdown(f"**{session.display_name}**" + (" · admin" if session.is_admin else ""))
        if st.button("Wyloguj"):
            del st.session_state["login"]
            st.rerun()

    pages = st.navigation([
        st.Page(lambda: zdarzenia.render(session), title="Zdarzenia", icon="🚨", url_path="zdarzenia", default=True),
        st.Page(lambda: obserwacje.render(session), title="Obserwacje", icon="👁", url_path="obserwacje"),
        st.Page(lambda: zlecenia.render(session), title="Zlecenia", icon="🛠", url_path="zlecenia"),
        st.Page(lambda: ustawienia.render(session), title="Ustawienia", icon="⚙️", url_path="ustawienia"),
    ])
    pages.run()


def main() -> None:
    session = st.session_state.get("login")
    if session is not None:
        reason = check_session_timeout(session)
        if reason:
            del st.session_state["login"]
            st.warning("Sesja wygasła. Zaloguj się ponownie.")
            st.rerun()
        bump_activity(session)
        dashboard_view(session)
    else:
        login_view()


main()
