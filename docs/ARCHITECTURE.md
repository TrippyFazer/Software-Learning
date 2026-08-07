# Architecture

## System overview

```
Internet
   ↓
DNS (learn.example.com → Lightsail static IP)
   ↓
AWS Lightsail — Ubuntu
   ↓  (only ports 22, 80, 443 open)
Caddy  ── automatic HTTPS, security headers
   ├── /api/*  →  api container (FastAPI, uvicorn)
   └── /*      →  static web bundle (React SPA)
              ↓
        PostgreSQL (internal Docker network only)
```

Three containers, one Compose file (the "web" tier exists as a build stage,
not a runtime process — the React bundle is compiled into the Caddy image by
a multi-stage build, so no Node runs in production):

| Container  | Image source                  | Exposed to internet | Role |
| ---------- | ----------------------------- | ------------------- | ---- |
| `caddy`    | `infra/docker/caddy.Dockerfile` (Node build stage → Caddy + bundle) | 80, 443 | TLS termination, routing, static files, security headers |
| `api`      | `infra/docker/api.Dockerfile` | no (internal :8000) | All application logic |
| `postgres` | `postgres:16`                 | **never**           | Learner state |

## Modular monolith

One API process, internally organized into modules with clear ownership:

```
apps/api/app/
  main.py            FastAPI app assembly, middleware, health endpoint
  core/              settings, db session, security primitives, logging
  modules/
    auth/            login, sessions, rate limiting
    content/         curriculum loading & validation (reads content/, read-only)
    learning/        attempts, mastery, flashcards, progress, review
    simterm/         virtual filesystem + command interpreter (pure simulation)
```

Modules communicate through ordinary Python imports of each other's public
service functions — no internal HTTP, no events, no queues. If two modules
need the same data, one owns it and exposes a function. This is the whole
point of the modular monolith (ADR-0006): boundaries you can learn from,
without distributed-systems overhead.

## The content/state boundary (the most important design decision)

**Git owns the curriculum. PostgreSQL owns the learner.**

| Lives in `content/` (git)         | Lives in PostgreSQL              |
| --------------------------------- | -------------------------------- |
| Modules, lessons, lesson body     | User account, session tokens     |
| Concepts and their metadata       | Attempts (quiz, exercise, challenge) |
| Vocabulary terms                  | Per-concept mastery records      |
| Quiz questions and answers        | Flashcard review history         |
| Terminal exercises & goal states  | Learning sessions, bookmarks     |
| Flashcard definitions             | Progress / completion state      |
| Boss challenges                   |                                  |

Consequences:

- Editing a lesson is a git commit, reviewable and revertible. No CMS.
- The database can be dropped and recreated without losing any curriculum.
- Learner state references content by **stable slug** (e.g. concept
  `docker-volume`, lesson `linux/filesystem`). Slugs are contracts.
- At startup (and on demand in dev) the content loader parses and validates
  everything in `content/`; malformed content fails fast with a precise error.

See ADR-0002 and ADR-0003.

## Domain model

Content-side entities (parsed from files, never stored in PG):

- **Module** — ordered group of lessons within a stage (`module.yaml`)
- **Lesson** — Markdown + frontmatter; sections follow the standard lesson
  format (mental model, vocabulary, deep dive, connections, practice, …)
- **Concept** — the atomic unit of mastery, declared in module/lesson
  frontmatter
- **VocabularyTerm** — plain + technical definition, why-it-matters, related
- **Exercise** — simulated-terminal task with a goal-state spec
- **QuizQuestion** — MCQ or free-response, keyed to concepts
- **Flashcard** — term → definition pairs keyed to concepts
- **ProjectChallenge / LabScenario ("boss")** — cumulative multi-concept
  challenge with a scenario state and success spec

Database-side entities (SQLAlchemy models):

- **User** — single learner in v0.1, but modeled normally
- **Session** — opaque token (hashed at rest), expiry, revocation
- **Attempt** — one submission against a quiz question, exercise, or
  challenge; stores the answer payload, correctness, and timestamps.
  Append-only: this is the raw evidence future spaced review needs.
- **MasteryRecord** — one row per (user, concept slug); current score plus
  the evidence counters that produced it (see mastery model below)
- **FlashcardState** — per-card review state (last seen, ease bucket) —
  minimal now, sufficient for a real SRS later
- **LearningSession** — coarse "sat down and studied" spans for the dashboard
- **LessonProgress** — per-lesson started/completed markers
- **LoginAttempt** — for rate limiting / lockout

Deliberately *not* over-normalized: concepts, lessons, and questions are
referenced by slug strings, not foreign-keyed lookup tables mirroring git.

## Mastery model (v0.1)

Mastery is per **concept**, computed from evidence, and explainable:

```
evidence types                        weight
  introduced (lesson completed)        0.15
  quiz accuracy (rolling)              0.35
  exercise passed                      0.30
  challenge/applied passed             0.20
retention decay: none in v0.1 (data preserved for it)
```

Score = weighted sum of achieved evidence, shown to the learner *with its
breakdown*. The algorithm lives in one file
(`modules/learning/mastery.py`) with the table above as code + docstring.
It is intentionally naive; ADR notes forbid making it opaque.

## Simulated terminal

A pure-Python virtual filesystem (an in-memory tree, JSON-serializable) plus
a small command interpreter supporting an educational command set (`pwd`,
`ls`, `cd`, `mkdir`, `touch`, `cat`, `cp`, `mv`, `rm`, `echo`, `whoami`,
plus `ls -l`/permissions-flavored commands as lessons need them).

- Input is parsed by our own tokenizer — **never** passed to a shell.
- Exercises are evaluated against the **resulting filesystem state**, not
  the command strings typed, so equivalent approaches pass.
- Exercise state (current VFS snapshot) round-trips through the API so the
  learner can leave and resume; snapshots are stored on the Attempt.
- Failure-driven exercises start from an intentionally broken initial state
  (wrong permissions, missing file, dead "service") defined in content.

Security argument and enforcement tests: `docs/SECURITY.md` §Simulated
terminal, `apps/api/tests/test_simterm_safety.py`, ADR-0004.

## Frontend

React SPA (Vite, TypeScript), npm-managed (ADR-0001). Pages:

Dashboard · Curriculum (map) · Module · Lesson · Practice (terminal) ·
Vocabulary · Review (flashcards) · Progress · About This Server · Login

- Server state via TanStack Query; no global state library beyond it.
- Lesson Markdown rendered client-side with a hardened renderer (no raw
  HTML pass-through).
- Diagram component: a small reusable "stack diagram" (list of connected
  nodes, each clickable to reveal an explanation) — deliberately not a
  graphics engine.
- Terminal UI: input line + scrollback, backed entirely by API calls.

## Observability

- `GET /api/health` — checks DB connectivity and content-load status.
- Structured JSON logs from the API (request id, path, status, duration).
- Docker `healthcheck` on api and postgres.
- Disk/db monitoring is documented as manual procedure in DEPLOYMENT.md
  (no monitoring stack in v0.1).

## Future boundaries (design-only in v0.1)

- **Real lab runner (v0.2+):** web app → Lab API → dedicated runner host /
  rootless isolation → ephemeral sandboxes. The web/api containers never get
  the Docker socket; the runner is a separate trust zone. ADR-0005.
- **AI tutor:** supplements, never replaces, versioned curriculum.
- **Brain Core connector:** outbound-only export of learning state
  (e.g. "learner UNDERSTANDS docker-volume") through a narrow API client;
  Learning Lab remains fully functional without it. See ROADMAP.md.
