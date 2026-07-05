"""Warstwa DB apki — instancja fam_config_db.Database + integracja tabel FAM.

Database tworzy tabele aplikacji (Base) i app_settings (FamBase). Dodatkowo
tworzymy tabelę login_attempts z fam_auth (rate-limit). To pokazuje wzorzec
łączenia modułów FAM: każdy ma swój Base, app spina je w jednym pliku SQLite.
"""

from __future__ import annotations

from pathlib import Path

from fam_auth import Base as AuthBase  # login_attempts
from fam_config_db import Database, SettingsStore

from .models import Base

_db: Database | None = None


def build_db(path: str | Path = "data/app.db") -> Database:
    db = Database(
        path,
        Base,
        added_columns={
            # przykład: gdy dodasz pole do modelu, dopisz tu by zmigrować istniejące bazy
            # "users": [("phone", "VARCHAR(20) DEFAULT ''")],
        },
    )
    db.init()
    # Tabela login_attempts (fam_auth) w tym samym pliku SQLite.
    AuthBase.metadata.create_all(db.engine)
    return db


def get_db() -> Database:
    global _db
    if _db is None:
        from .settings import settings

        _db = build_db(settings().db_path)
    return _db


def get_settings_store() -> SettingsStore:
    return SettingsStore(get_db())
