"""
Utwórz/zaktualizuj konto admina (idempotentne).

    python -m scripts.bootstrap_admin <login> <haslo> [display_name]

Albo w kontenerze:
    docker exec -it <app> python -m scripts.bootstrap_admin admin "haslo" "Administrator"
"""

from __future__ import annotations

import sys

from fam_auth import hash_password
from sqlalchemy import func, select

from app.db import get_db
from app.models import User


def bootstrap_admin(login: str, password: str, display_name: str = "") -> None:
    db = get_db()
    with db.session() as s:
        user = s.scalar(select(User).where(func.lower(User.username) == login.lower()))
        if user is None:
            user = User(username=login, is_admin=True)
            s.add(user)
        user.password_hash = hash_password(password)
        user.display_name = display_name or login
        user.is_admin = True
        s.commit()
    print(f"OK: admin '{login}' gotowy.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    bootstrap_admin(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
