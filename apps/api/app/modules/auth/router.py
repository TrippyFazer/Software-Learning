"""Auth endpoints: login, logout, whoami."""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.settings import get_settings
from app.modules.auth import service
from app.modules.auth.deps import CurrentUser

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)


class MeResponse(BaseModel):
    email: str
    display_name: str


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,                    # invisible to JavaScript
        secure=settings.cookie_secure,    # HTTPS-only in production
        samesite="lax",                   # CSRF mitigation for state-changing posts
        path="/",
    )


@router.post("/login", response_model=MeResponse)
def login(body: LoginRequest, response: Response, db: Annotated[Session, Depends(get_db)]):
    try:
        user, token = service.login(db, body.email, body.password)
    except service.LoginLocked as e:
        raise HTTPException(
            status_code=429, detail="Too many failed attempts. Try again later."
        ) from e
    except service.LoginRejected as e:
        # Same message for unknown email and wrong password — deliberate.
        raise HTTPException(status_code=401, detail="Invalid email or password") from e
    _set_session_cookie(response, token)
    return MeResponse(email=user.email, display_name=user.display_name)


@router.post("/logout")
def logout(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    ill_session: Annotated[str | None, Cookie(alias="ill_session")] = None,
):
    if ill_session:
        service.logout(db, ill_session)
    response.delete_cookie(get_settings().session_cookie_name, path="/")
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser):
    return MeResponse(email=user.email, display_name=user.display_name)
