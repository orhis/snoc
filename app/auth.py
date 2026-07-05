"""Logowanie — spina fam_auth (verify, rate-limit, 2FA) z warstwą DB apki.

Przepływ: rate-limit gate -> weryfikacja hasła -> (opcjonalnie) 2FA -> sesja.
Każda próba (sukces/porażka) zapisywana do login_attempts (audyt + rate-limit).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from fam_auth import (
    RateLimitExceeded,
    check_login_allowed,
    record_attempt,
    verify_code,
    verify_password,
)
from fam_config_db import Database
from sqlalchemy import func

from .models import User

__all__ = ["LoginSession", "InvalidCredentials", "TwoFactorRequired", "authenticate", "RateLimitExceeded"]


@dataclass
class LoginSession:
    """Obiekt sesji trzymany w st.session_state. created_at/last_activity_at
    pasują do fam_auth.session_timeout (duck typing)."""

    username: str
    display_name: str
    is_admin: bool
    created_at: datetime
    last_activity_at: datetime


class InvalidCredentials(Exception):
    pass


class TwoFactorRequired(Exception):
    """Hasło OK, ale user ma 2FA i nie podał (poprawnego) kodu."""


def authenticate(
    db: Database,
    username: str,
    password: str,
    *,
    code: str | None = None,
    ip: str = "unknown",
) -> LoginSession:
    """Zwraca LoginSession albo rzuca: RateLimitExceeded / InvalidCredentials /
    TwoFactorRequired."""
    with db.session() as s:
        check_login_allowed(s, username)  # RateLimitExceeded gdy za dużo prób

        user = s.scalar(select_user(username))
        password_ok = bool(user) and verify_password(password, user.password_hash)

        # 2FA tylko gdy hasło OK i user ma skonfigurowany secret
        if password_ok and user.totp_secret:
            if not code:
                # nie zapisujemy jako fail — hasło było dobre, czekamy na kod
                raise TwoFactorRequired
            if not verify_code(user.totp_secret, code):
                record_attempt(s, username, ip, success=False)
                s.commit()
                raise InvalidCredentials

        record_attempt(s, username, ip, success=password_ok)
        s.commit()

        if not password_ok:
            raise InvalidCredentials

        now = datetime.now(UTC)
        return LoginSession(
            username=user.username,
            display_name=user.display_name or user.username,
            is_admin=user.is_admin,
            created_at=now,
            last_activity_at=now,
        )


def select_user(username: str):
    from sqlalchemy import select

    return select(User).where(func.lower(User.username) == username.lower().strip())
