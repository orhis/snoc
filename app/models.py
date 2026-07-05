"""Modele apki (DeclarativeBase aplikacji). LoginAttempt dostarcza fam_auth
na własnym Base — tworzymy go obok w db.py."""

from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(128), default="")
    totp_secret: Mapped[str] = mapped_column(String(64), default="")  # 2FA (puste = wyłączone)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
