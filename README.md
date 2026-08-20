# Infrastructure Learning Lab

A private, single-learner web platform for learning software engineering and
infrastructure from the ground up: Linux, networking, SSH, storage, Docker,
databases, web applications, and eventually AI application development.

The platform is built for one learner with a biomedical engineering background
who is simultaneously building **Brain Core** (a personal/organizational
intelligence platform) and a future **Plex/home-server** environment. Lessons
constantly connect abstract concepts back to those two real systems — including
the very server this application runs on.

## Teaching philosophy

```
LEARN → VISUALIZE → PRACTICE → MAKE A MISTAKE → UNDERSTAND WHY
      → TRY AGAIN → APPLY → REVIEW LATER
```

- Mental models before terminology.
- Practice in a **simulated terminal** — safe to break, impossible to damage
  the host (see [docs/SECURITY.md](docs/SECURITY.md)).
- Mastery is tracked per **concept**, with transparent, explainable scoring —
  not "lesson completed = learned".
- **Works on a plane.** Lessons, vocabulary and flashcards are downloadable to
  the device and the app installs like a native one; anything you complete
  offline is queued and synced on reconnect. Terminal exercises need the
  server, and the app says so rather than pretending. See
  [ADR-0007](docs/ADR/0007-offline-first-pwa.md).
- Failure-driven exercises: some start broken on purpose.
- The deployment itself is part of the curriculum ("About This Server").

## Stack

| Layer          | Technology                                        |
| -------------- | ------------------------------------------------- |
| Backend        | Python 3.13, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, Psycopg 3 |
| Frontend       | TypeScript, React, Vite                           |
| Database       | PostgreSQL 16                                     |
| Deployment     | Docker Compose on AWS Lightsail (Ubuntu)          |
| Reverse proxy  | Caddy (automatic HTTPS)                           |
| Python deps    | uv                                                |
| Frontend deps  | npm (see ADR-0001)                                |

Architecture: **modular monolith**. One API process, one web bundle, one
database. No Kubernetes, no microservices, no message queues. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Repository layout

```
apps/api/          FastAPI backend (modular monolith)
apps/web/          React + Vite frontend
content/           Version-controlled curriculum (Markdown + YAML frontmatter)
  modules/         Lessons, organized by module
  vocabulary/      Vocabulary term definitions
  exercises/       Terminal exercise definitions
  quizzes/         Quiz question banks
  flashcards/      Flashcard decks
docs/              Architecture, curriculum plan, security, deployment, ADRs
infra/docker/      Dockerfiles and Caddyfile
infra/lightsail/   Lightsail-specific deployment assets
scripts/           Operational scripts (user creation, backup, restore)
```

Curriculum **content lives in git**; learner **state lives in PostgreSQL**.
That boundary is deliberate — see ADR-0002 and ADR-0003.

## Local development

Prerequisites: Docker + Docker Compose, or natively `uv` + Node 22.

```bash
cp .env.example .env        # then edit values (HTTP_PORT=8080 if 80 is taken)
docker compose up --build
# web:  http://localhost  (or http://localhost:$HTTP_PORT)
```

Create the learner account (reads BOOTSTRAP_* from .env):

```bash
docker compose exec api python -m scripts.create_user
```

Native backend development:

```bash
cd apps/api
uv sync
uv run pytest                # run the test suite
uv run uvicorn app.main:app --reload
```

Native frontend development:

```bash
cd apps/web
npm install
npm run dev                  # proxies /api to localhost:8000
npm test
```

## Deployment

Full Lightsail runbook: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
Security model and exposed ports: [docs/SECURITY.md](docs/SECURITY.md).

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system design and boundaries
- [docs/CURRICULUM.md](docs/CURRICULUM.md) — full 31-module curriculum plan
- [docs/SECURITY.md](docs/SECURITY.md) — threat model, hard rules, ports
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — Lightsail runbook
- [docs/ROADMAP.md](docs/ROADMAP.md) — v0.1 scope and future versions
- [docs/ADR/](docs/ADR/) — architectural decision records
- [V0_1_STATUS.md](V0_1_STATUS.md) — current release status

## v0.1 scope (deliberately small)

Authentication, dashboard, curriculum map, lesson pages, vocabulary, quizzes,
attempt tracking, concept mastery, flashcards, a simulated Linux terminal,
Modules 0–3 with representative lessons, one Stage 1 boss challenge, and
Lightsail deployment. Nothing else — see [docs/ROADMAP.md](docs/ROADMAP.md)
for what is intentionally deferred (real command labs, AI tutor, Brain Core
integration).
