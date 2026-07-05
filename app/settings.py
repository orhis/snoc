"""Konfiguracja apki — rozszerza BaseAppSettings z FAM (czyta .env)."""

from __future__ import annotations

from fam_config_db import BaseAppSettings, get_settings


class Settings(BaseAppSettings):
    # Admin break-glass (hash z scripts/bootstrap_admin.py albo fam_auth.hash_password)
    admin_login: str = "admin"
    admin_password_hash: str = ""

    # Baza
    db_path: str = "data/app.db"

    # SMTP (opcjonalnie — pod moduł email gdy dojdzie)
    smtp_host: str = ""
    smtp_port: int = 587

    # 2FA wymagane dla adminów?
    require_2fa: bool = False


def settings() -> Settings:
    return get_settings(Settings)
