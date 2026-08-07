"""Application settings, loaded from environment variables (and .env in dev).

Every knob the operator can turn is declared here with a safe default and a
comment. See .env.example at the repository root for the operator-facing view.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # "production" turns on Secure cookies and refuses obviously-unsafe config.
    app_env: Literal["development", "production", "test"] = "development"
    public_hostname: str = "learn.example.com"

    # Database — assembled into a URL below; postgres is never internet-exposed.
    postgres_user: str = "learninglab"
    postgres_password: str = "learninglab"
    postgres_db: str = "learninglab"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Sessions
    session_secret: str = "dev-only-secret-change-me"
    session_ttl_hours: int = 336
    session_cookie_name: str = "ill_session"

    # Login protection
    login_max_attempts: int = 8
    login_window_seconds: int = 900
    login_lockout_seconds: int = 900

    # Curriculum content
    content_root: str = "../../content"
    content_hot_reload: bool = True

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cookie_secure(self) -> bool:
        return self.app_env == "production"

    def validate_production_safety(self) -> None:
        """Refuse to boot production with development secrets in place."""
        if self.app_env != "production":
            return
        problems = []
        if "change-me" in self.session_secret or self.session_secret.startswith("dev-only"):
            problems.append("SESSION_SECRET is a placeholder")
        if len(self.session_secret) < 32:
            problems.append("SESSION_SECRET is too short (<32 chars)")
        if "change-me" in self.postgres_password or self.postgres_password == "learninglab":
            problems.append("POSTGRES_PASSWORD is a placeholder")
        if problems:
            raise RuntimeError(
                "Refusing to start in production with unsafe configuration: "
                + "; ".join(problems)
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
