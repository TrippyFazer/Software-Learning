"""Create (or update the password of) the learner account.

Reads BOOTSTRAP_USER_EMAIL / BOOTSTRAP_USER_PASSWORD / BOOTSTRAP_USER_NAME
from the environment. There is deliberately no signup endpoint — account
creation is an operator action:

    docker compose exec api python -m scripts.create_user
"""

import os
import sys

from sqlalchemy import select

from app.core.db import get_sessionmaker
from app.modules.auth import service
from app.modules.auth.models import User
from app.modules.auth.security import hash_password


def main() -> int:
    email = os.environ.get("BOOTSTRAP_USER_EMAIL", "").strip().lower()
    password = os.environ.get("BOOTSTRAP_USER_PASSWORD", "")
    name = os.environ.get("BOOTSTRAP_USER_NAME", "Learner")

    if not email or not password:
        print("ERROR: set BOOTSTRAP_USER_EMAIL and BOOTSTRAP_USER_PASSWORD (see .env.example)")
        return 1
    if "change-me" in password or len(password) < 12:
        print("ERROR: refusing to create a user with a placeholder or <12-char password")
        return 1

    with get_sessionmaker()() as db:
        existing = db.scalar(select(User).where(User.email == email))
        if existing:
            existing.password_hash = hash_password(password)
            db.commit()
            print(f"Updated password for existing user {email}")
        else:
            service.create_user(db, email, password, name)
            db.commit()
            print(f"Created user {email}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
