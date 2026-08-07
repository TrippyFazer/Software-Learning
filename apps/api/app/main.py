"""Application assembly.

The modular monolith's single entry point: builds the FastAPI app, wires
middleware, mounts each module's router under /api, and exposes the health
endpoint. Everything interesting lives in the modules (ADR-0006).
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from sqlalchemy import text

from app.core.db import get_engine
from app.core.logging import configure_logging
from app.core.settings import get_settings
from app.modules.auth.router import router as auth_router

logger = logging.getLogger("app.request")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    settings.validate_production_safety()
    # Load (and validate) the curriculum up front: bad content should stop
    # the boot, not 500 at request time (ADR-0002).
    from app.modules.content.loader import get_content_index

    index = get_content_index()
    logging.getLogger("app").info(
        "startup complete",
        extra={"event": "startup"},
    )
    logging.getLogger("app").info(
        f"content loaded: {len(index.modules)} modules, {len(index.lessons)} lessons, "
        f"{len(index.concepts)} concepts"
    )
    yield


app = FastAPI(title="Infrastructure Learning Lab", docs_url=None, redoc_url=None, lifespan=lifespan)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    """One structured log line per request; the request id ties errors together."""
    request_id = uuid.uuid4().hex[:12]
    start = time.perf_counter()
    response = await call_next(request)
    logger.info(
        "request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round((time.perf_counter() - start) * 1000, 1),
        },
    )
    response.headers["X-Request-Id"] = request_id
    return response


@app.get("/api/health")
def health():
    """Liveness + dependency check for Docker healthchecks and humans."""
    checks: dict[str, str] = {}
    ok = True
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unreachable"
        ok = False
    try:
        from app.modules.content.loader import get_content_index

        idx = get_content_index()
        checks["content"] = f"ok ({len(idx.lessons)} lessons)"
    except Exception as e:
        checks["content"] = f"error: {type(e).__name__}"
        ok = False
    return {"status": "ok" if ok else "degraded", "checks": checks}


app.include_router(auth_router, prefix="/api")

from app.modules.content.router import router as content_router  # noqa: E402
from app.modules.learning.router import router as learning_router  # noqa: E402
from app.modules.simterm.router import router as simterm_router  # noqa: E402

app.include_router(content_router, prefix="/api")
app.include_router(learning_router, prefix="/api")
app.include_router(simterm_router, prefix="/api")
