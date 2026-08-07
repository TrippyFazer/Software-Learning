# FastAPI backend image. Build context: apps/api/
#
# Two ideas worth noticing (both become course material later):
#   1. Dependencies are installed from the lockfile BEFORE the source is
#      copied, so code edits don't invalidate the dependency layer cache.
#   2. The app runs as a non-root user — a container compromise shouldn't
#      hand out root, even inside the sandbox (docs/SECURITY.md rule 3).

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependency layer (cached until pyproject/uv.lock change)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Application source
COPY . .
RUN uv sync --frozen --no-dev

# Non-root runtime user
RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
