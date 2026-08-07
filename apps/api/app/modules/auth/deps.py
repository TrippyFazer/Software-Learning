"""FastAPI dependencies for authentication."""

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.settings import get_settings
from app.modules.auth import service
from app.modules.auth.models import User


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    ill_session: Annotated[str | None, Cookie(alias="ill_session")] = None,
) -> User:
    """Resolve the session cookie to a user or 401. Every learner-facing
    endpoint depends on this — there are no anonymous features."""
    # Cookie alias must match settings.session_cookie_name (static so FastAPI
    # can build the OpenAPI schema at import time).
    assert get_settings().session_cookie_name == "ill_session"
    if ill_session is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = service.resolve_session(db, ill_session)
    if user is None:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
