# -*- coding: utf-8 -*-
"""Test UI logowania przez streamlit AppTest — łapie to, czego smoke HTTP nie widzi
(regresja buga: kolizja key formularza 'login' z session_state['login'])."""
import pytest


@pytest.fixture()
def app(tmp_path, monkeypatch):
    from fam_auth import hash_password
    from fam_config_db import Database
    from app.models import Base, User
    from app import db as appdb

    db = Database(str(tmp_path / "ui.db"), Base)
    db.init()
    import fam_auth
    fam_auth.Base.metadata.create_all(db.engine)   # login_attempts (rate-limit)
    with db.session() as s:
        s.add(User(username="tester", password_hash=hash_password("sekret123"),
                   display_name="Tester", is_admin=True))
        s.commit()
    monkeypatch.setattr(appdb, "_db", db)

    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file("app/streamlit_app.py", default_timeout=30)
    return at


def test_login_happy_path_bez_wyjatku(app):
    at = app.run()
    assert not at.exception, at.exception
    at.text_input[0].set_value("tester")
    at.text_input[1].set_value("sekret123")
    at.button[0].set_value(True)  # submit formularza
    at.run()
    # SEDNO REGRESJI: zapis sesji nie może rzucić StreamlitAPIException (kolizja kluczy)
    assert not at.exception, f"wyjątek po zalogowaniu: {at.exception}"
    assert "login" in at.session_state


def test_zle_haslo_komunikat_bez_wyjatku(app):
    at = app.run()
    at.text_input[0].set_value("tester")
    at.text_input[1].set_value("zle-haslo")
    at.button[0].set_value(True)
    at.run()
    assert not at.exception
    assert at.error, "brak komunikatu o błędnym logowaniu"
