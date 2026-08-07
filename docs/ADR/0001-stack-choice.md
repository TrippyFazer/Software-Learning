# ADR-0001: Technology stack

Status: Accepted · Date: 2026-08-07

## Context

The Learning Lab must run on a small Lightsail instance, be maintainable by
one person, and — critically — use technology that transfers directly to
Brain Core development, because reading this codebase is itself part of the
curriculum.

## Decision

- **Backend:** Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic,
  Psycopg 3, managed with **uv**.
- **Frontend:** TypeScript, React 18, Vite, TanStack Query.
- **Database:** PostgreSQL 16.
- **Deployment:** Docker Compose; **Caddy** for reverse proxy + automatic TLS.
- **Testing:** pytest (backend), Vitest + Testing Library (frontend).
- **Frontend package manager: npm.** pnpm was considered (faster installs,
  stricter node_modules); npm chosen because it ships with Node, removes one
  install step from every environment (CI, Lightsail, contributor machines),
  and its lockfile format is the ecosystem default. For a single small app
  the pnpm advantages don't pay for the extra moving part. Revisit only if
  install times actually hurt.

## Consequences

- One language per tier, all mainstream, all with excellent documentation —
  a learner can search any error message and find answers.
- Caddy trades Nginx's ubiquity for config that fits on one screen and
  hands-free TLS; Nginx is taught conceptually in the curriculum anyway.
- uv gives lockfile-reproducible Python environments without Poetry/pipenv
  complexity.
- Rejected: Kubernetes, Kafka, microservices, Redis (until proven needed),
  graph DBs, vector DBs, serverless — each adds operational surface that
  obscures rather than teaches at this stage.
