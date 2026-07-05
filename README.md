# Szkielet FAM — „pusta apka" do klonowania

Działający szkielet Streamlit spinający trzy moduły FAM w fundament nowej apki:
**logowanie** (hasło + opcjonalne 2FA, rate-limit, timeout sesji) + **baza/config** + **Docker/deploy**. Klonujesz, dokładasz logikę.

```
skeleton/
  app/
    streamlit_app.py   # entry: login gate + dashboard
    settings.py        # Settings(BaseAppSettings) — czyta .env
    db.py              # Database (fam_config_db) + tabela login_attempts (fam_auth)
    models.py          # Base + User
    auth.py            # authenticate(): rate-limit -> hasło -> 2FA -> LoginSession
  scripts/bootstrap_admin.py
  tests/test_wiring.py # smoke: dowód że moduły się spinają (7 testów)
  Dockerfile · docker-compose.yml · .dockerignore   # wygenerowane przez fam_deploy
  requirements.txt · .env.example · .streamlit/config.toml
```

Status: 🟢 **7 testów wiring** — logowanie OK/błędne, rate-limit, 2FA, settings store, timeout sesji.

## Co używa z FAM
| Z modułu | Czego |
|---|---|
| `fam_auth` | `hash_password`/`verify_password`, `check_login_allowed`/`record_attempt` (rate-limit), `verify_code` (2FA), `check_session_timeout`/`bump_activity`, `Base` (login_attempts) |
| `fam_config_db` | `Database` (SQLite WAL + auto-migracja), `BaseAppSettings`/`get_settings` (.env), `SettingsStore` |
| `fam_deploy` | wygenerował `Dockerfile` + `docker-compose.yml` + `.dockerignore` |

## Start (dev)
```bash
python -m venv .venv && . .venv/Scripts/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt                      # ciągnie fam_* z repo (git)
cp .env.example .env                                 # uzupełnij
python -m scripts.bootstrap_admin admin "twoje-haslo" "Administrator"
streamlit run app/streamlit_app.py
```

> Testy w tym repo działają bez instalacji fam_* — `conftest.py` bierze moduły z `../modules`.
> W sklonowanym projekcie usuwasz ten shim i polegasz na `pip install`.

## Jak zacząć nowy projekt z tego szkieletu
1. Skopiuj `skeleton/` do nowego repo (np. `orhis/mojaapka`).
2. W `requirements.txt` zostaw zależności `fam_*` (instalują się z FAM).
3. Dodaj swoje modele w `app/models.py`, strony w `app/` (Streamlit multipage).
4. Wygeneruj świeży Docker pod swoją nazwę/port:
   `python -m fam_deploy --app-name mojaapka --port 8504 --with-scheduler` (jeśli trzeba).
5. Deploy: patrz `modules/deploy/DEPLOY-synology.md`.

## Czego tu (jeszcze) nie ma
Email/SMTP, Google OIDC, audit log, scheduler — są w indexie FAM jako kolejne moduły do wyciągnięcia. Dokładasz, gdy apka ich potrzebuje.
