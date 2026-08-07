# CLAUDE.md — working on Infrastructure Learning Lab

Guidance for AI coding assistants (and future humans) working in this repo.

## What this is

A private single-learner web platform teaching infrastructure and software
engineering. The learner has a biomedical engineering background, no formal CS
training, and is building this partly *to understand systems like this one*.
The codebase itself is a teaching artifact: prefer clear, conventional code
over clever code, and comment the "why" where a newcomer would ask it.

## Hard rules (never violate)

1. **No host command execution from the web app.** The terminal is a
   simulation (`apps/api/app/modules/simterm/`). It must never call
   `subprocess`, `os.system`, `exec`, or similar on learner input. Tests in
   `apps/api/tests/test_simterm_safety.py` enforce this — keep them passing.
2. **No Docker socket in the web/api containers. No sudo. No privileged mode.**
3. **PostgreSQL is never published to the internet.** It lives only on the
   internal Docker network.
4. **No secrets in git.** Only `.env.example` with placeholders.
5. **Sessions are opaque server-side tokens in HttpOnly cookies.** Do not
   introduce localStorage JWTs.
6. **Curriculum content is canonical in `content/`, not in the database and
   not in React components.** The database stores learner state only.

## Architecture in one paragraph

Modular monolith. `apps/api` is a FastAPI app organized as modules
(`auth`, `content`, `learning`, `simterm`) sharing one PostgreSQL database via
SQLAlchemy 2.x + Alembic. `apps/web` is a React/Vite SPA that talks to the API
under `/api/*`. Caddy terminates TLS and routes `/api/*` to the API container
and everything else to the static web bundle. See `docs/ARCHITECTURE.md` and
`docs/ADR/`.

## Commands

```bash
# Backend (from apps/api/)
uv sync                       # install deps
uv run pytest                 # full test suite — run before committing
uv run pytest tests/test_simterm_safety.py   # the security-critical tests
uv run alembic upgrade head   # apply migrations
uv run alembic revision --autogenerate -m "msg"

# Frontend (from apps/web/)
npm install
npm run dev
npm run build                 # type-checks then bundles
npm test

# Full stack
docker compose up --build
```

## Conventions

- Python: ruff-formatted, type-hinted, Pydantic models for all API I/O.
- Content files: Markdown with YAML frontmatter. Schemas are validated by
  `apps/api/app/modules/content/loader.py`; invalid content should fail
  loudly at load time, not 500 at request time.
- IDs in content are stable slugs (`linux/filesystem`), referenced by
  database rows; never rename a slug without a migration note.
- Mastery scoring lives in `apps/api/app/modules/learning/mastery.py` and is
  deliberately simple and documented. Don't "improve" it into opacity.
- New meaningful decisions get an ADR in `docs/ADR/`.

## Scope discipline

v0.1 is finished (see `V0_1_STATUS.md`). Do not add: real command execution,
Docker sandboxes, AI tutoring, Brain Core integration, multi-user features,
or additional modules beyond 0–3 — unless the learner explicitly asks.
