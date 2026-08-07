"""Authentication service: login, logout, session resolution, rate limiting.

All functions take an explicit SQLAlchemy session — the router owns request
wiring, this module owns the rules.
"""

import logging
from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.core.settings import get_settings
from app.modules.auth import security
from app.modules.auth.models import AuthSession, LoginAttempt, User

logger = logging.getLogger(__name__)


class LoginRejected(Exception):
    """Raised for any failed login. One message for every cause on purpose:
    distinguishing "no such user" from "wrong password" leaks which emails
    have accounts."""


class LoginLocked(Exception):
    """Too many recent failures for this account."""


def _recent_failures(db: Session, email: str) -> int:
    settings = get_settings()
    window_start = utcnow() - timedelta(seconds=settings.login_window_seconds)
    return db.scalar(
        select(func.count())
        .select_from(LoginAttempt)
        .where(LoginAttempt.email == email, LoginAttempt.attempted_at >= window_start)
    ) or 0


def login(db: Session, email: str, password: str) -> tuple[User, str]:
    """Authenticate; return (user, raw_session_token) or raise.

    Rate limiting counts failures per email within a sliding window; hitting
    the cap refuses further tries (even correct ones) until the window drains.
    """
    settings = get_settings()
    email = email.strip().lower()

    if _recent_failures(db, email) >= settings.login_max_attempts:
        logger.warning("login locked out", extra={"event": "login_lockout"})
        raise LoginLocked()

    user = db.scalar(select(User).where(User.email == email))
    # Verify against a dummy hash when the user doesn't exist so response
    # timing doesn't reveal whether the email is registered.
    if user is None:
        security.verify_password(security.hash_password("timing-equalizer"), password)
        ok = False
    else:
        ok = security.verify_password(user.password_hash, password)

    if not ok or user is None:
        db.add(LoginAttempt(email=email))
        logger.warning("login failed", extra={"event": "login_failed"})
        raise LoginRejected()

    # Success: clear the failure slate and mint a session.
    db.execute(delete(LoginAttempt).where(LoginAttempt.email == email))
    token = security.new_session_token()
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=security.hash_session_token(token),
            expires_at=utcnow() + timedelta(hours=settings.session_ttl_hours),
        )
    )
    logger.info("login ok", extra={"event": "login_ok", "user_id": user.id})
    return user, token


def resolve_session(db: Session, token: str) -> User | None:
    """Map a cookie token to a live user, or None. Expired rows are deleted."""
    record = db.scalar(
        select(AuthSession).where(AuthSession.token_hash == security.hash_session_token(token))
    )
    if record is None:
        return None
    if record.expires_at <= utcnow():
        db.delete(record)
        return None
    return db.get(User, record.user_id)


def logout(db: Session, token: str) -> None:
    """Server-side revocation: the session row is gone, the cookie is dead."""
    db.execute(
        delete(AuthSession).where(AuthSession.token_hash == security.hash_session_token(token))
    )


def create_user(db: Session, email: str, password: str, display_name: str) -> User:
    """Operator-only (scripts/create_user.py) — there is no signup endpoint."""
    user = User(
        email=email.strip().lower(),
        display_name=display_name,
        password_hash=security.hash_password(password),
    )
    db.add(user)
    db.flush()
    return user
