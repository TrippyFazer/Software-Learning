# V0.1 Status

Date: 2026-08-07 · Branch: `claude/infrastructure-learning-lab-pgudc1`

## What works (verified, not hoped)

Every item below was exercised by automated tests and/or a real Chromium
session against the running app:

- **Authentication** — email+password, Argon2id, opaque server-side
  sessions in HttpOnly/SameSite=Lax cookies (Secure in production), real
  server-side revocation on logout, per-account rate limiting with
  lockout, single unified failure message, timing-equalized unknown-email
  path. Operator-only account creation (`scripts/create_user.py`).
- **Curriculum engine** — Markdown+YAML content parsed and validated at
  boot; malformed content stops the app with file+field errors (this
  caught three real authoring mistakes during development); cross-references
  (quiz/exercise/prerequisite/flashcard slugs) checked.
- **Content** — Modules 0–3 implemented with the full 12-section lesson
  format (mental model vs technical reality, Brain Core + Plex connections,
  common mistakes, summaries): 12 lessons, 45 vocabulary terms, 9 quizzes
  (44 questions), 44 flashcards, 6 terminal exercises (2 failure-driven),
  1 sandbox. All 31 modules visible on the curriculum map (27 as planned).
- **Quiz engine** — server-side grading; answer keys never leave the
  backend (verified structurally in tests); explanations revealed only
  after committing to an answer; text answers normalized.
- **Attempts & mastery** — append-only attempt log; transparent weighted
  mastery per concept (introduced 0.15 / quiz 0.35 / exercise 0.30 /
  applied 0.20) with a learner-visible breakdown that provably sums to the
  score; retention counters recorded but unweighted (reserved for a real
  SRS).
- **Flashcards** — Leitner boxes (1/3/7/14 days), due-card surfacing after
  lesson completion, full review history in the attempt log.
- **Simulated terminal** — pure in-memory VFS; `pwd ls cd mkdir touch cat
  cp mv rm echo whoami chmod help clear`, `;`/`&&` chaining, `>`/`>>`
  redirection, x-bit-gated `./script` execution with content-scripted
  output; exercises graded on resulting **state** so equivalent approaches
  pass (verified with two different solution routes); resumable state;
  reset.
- **Stage 1 boss (SERVER ROOKIE)** — downed web app, log-driven diagnosis,
  two distinct permission faults, 4 diagnosis questions; requires terminal
  goals AND correct diagnosis; completable end-to-end (verified).
- **Progress** — dashboard with stage/module/next-lesson/stats, per-module
  completion, weak-concept list, study-time tracking; state survives
  logout/login (tested — the "leave and come back" requirement).
- **UI** — responsive React SPA, dark technical-lab aesthetic; Login,
  Dashboard, Curriculum, Lesson, Practice, Challenge, Vocabulary, Review,
  Progress, About This Server (clickable architecture diagram of the real
  deployment, secrets-free).
- **Ops** — health endpoint (DB + content checks), structured JSON request
  logs, Docker healthchecks, log rotation, nightly-backup script with size
  sanity check, restore script with `--target` verification mode.

## Test results

- Backend: **62/62 passing** (`apps/api: uv run pytest`), ruff clean.
  Includes the security-critical suite: AST proof that the simterm package
  has no process/network/eval capability; runtime proof `subprocess`/`pty`
  never load; hostile inputs (`rm -rf /`, `$(reboot)`, backticks, path
  traversal) leave the host untouched; an automatic sweep asserting every
  API route requires authentication.
- Frontend: **7/7 passing** (Vitest), `tsc` clean, production build clean.
- E2E: Chromium (Playwright) session through login → lesson → quiz →
  terminal → About → Progress with zero JS errors.
- Tests found two real bugs before any user could: (1) ORM aliasing that
  silently dropped terminal-state writes; (2) failed-login records rolled
  back with the 401 response, which would have disabled rate limiting.

## Security review summary

Hard rules verified in this release (see docs/SECURITY.md):

| Rule | Status |
|------|--------|
| No learner input executed on host | ✅ enforced by design + AST/runtime/hostile-input tests |
| No Docker socket in containers | ✅ compose config checked: zero mounts |
| API container non-root | ✅ `USER app` |
| PostgreSQL never published | ✅ no `ports:` mapping; internal network only |
| No secrets in git | ✅ `.env` untracked; placeholders only in `.env.example` |
| Sessions HttpOnly/SameSite, hashed at rest | ✅ tested |
| Login rate limiting | ✅ tested (incl. the rollback bug fix) |
| Secure headers + CSP | ✅ in Caddyfile; markdown rendered without raw HTML |
| Production boot refuses placeholder secrets | ✅ `validate_production_safety` |

Residual risks, acknowledged: single-factor password auth (acceptable for a
single-user app with a strong password + rate limiting); Caddy/Postgres
image updates are manual (documented cadence in DEPLOYMENT.md); no
IP-restriction on SSH by default (optional hardening documented).

## Deployment status

**Not yet deployed to Lightsail** — this environment has no access to the
learner's AWS account or domain. Everything needed is ready:

- `docker-compose.yml` + `infra/docker/` (validated with `docker compose
  config`; container images could not be built in this sandbox because the
  network policy blocks Docker Hub's CDN — the Dockerfiles follow standard
  patterns and the identical app code runs verified under uvicorn/vite).
- `docs/DEPLOYMENT.md` — complete runbook: server prep, SSH hardening,
  two-layer firewall, Docker install, env config, first start, migrations,
  updates, backup/restore, log inspection, troubleshooting.
- Backup → restore verified against a scratch database (identical row
  counts) using the exact pg_dump/psql pipeline the scripts wrap, per the
  master plan's requirement. First action after real deployment: run
  `restore_db.sh --target learninglab_restore_test` once on the instance.

## Known limitations

- **Simulator fidelity**: no pipes, globbing, env vars, tab completion, or
  command history; permissions displayed and enforced for execution only
  (not read/write); `ls -l` timestamps are cosmetic. Each gap is
  acknowledged in lesson text where relevant.
- **Scripted execution is unconditional**: a content-defined "script"
  prints its output regardless of other VFS state (e.g. running
  `restart.sh` before fixing the config still prints the success text in
  the boss challenge — completion is still gated correctly on both goals).
  A conditional-execution spec is a natural v0.2 content-engine upgrade.
- **Free-response evaluation** is accept-list matching only; genuine
  explanation grading waits for the AI-tutor era.
- **"Needs review"** is a weak-mastery list + due flashcards, not a real
  spaced-repetition scheduler (data model is ready for one).
- **Module 0's architecture exercise** is a classify-and-inspect practice
  plus quiz, not a diagram-manipulation widget.
- Bookmarks (mentioned in the master plan's data list) were not built —
  nothing in v0.1 scope used them.
- Curriculum numbering: the master plan places Storage in Stage 1;
  CURRICULUM.md schedules its content with Stage 2 delivery (noted there).

## Technical debt

- `packages/` layer skipped: content schemas live in the API's content
  module (one consumer). Revisit only if a second consumer appears.
- Alembic migrations live in `apps/api/migrations/` rather than top-level
  `migrations/` — they are coupled to the API's models and run from its
  container.
- FastAPI's current version wraps included routers (`_IncludedRouter`);
  the auth-sweep test walks `original_router` — may need a tweak on
  framework upgrade.
- `starlette.testclient` deprecation warning (httpx2 migration) — cosmetic
  for now.
- Frontend has component tests only; no browser-automation suite in CI.

## Recommended next educational modules

Based on what Stage 1 sets up, in order:

1. **Module 8 (Docker)** — the learner will have just deployed this app
   with Compose; teaching from the app's own compose file while the
   deployment experience is fresh is the highest-leverage lesson available.
2. **Module 4 (Storage)** — completes the Stage 1 foundation; `df`/`du`
   simulator commands are cheap to add and unlock disk-full failure drills.
3. **Module 9 (Git)** — the learner edits curriculum through git already;
   make that self-referential.

## Proposed v0.2 experiments (validate by dogfooding first)

1. Simulator conditional execution + `grep`, `find`, `ps`, `df`, `du`,
   `free`, command history (↑), and richer failure scenarios.
2. A real (simple) spaced-review scheduler over the preserved attempt log
   (SM-2-lite on the existing Leitner state).
3. Retention checks: resurface old quiz questions after N days and start
   weighting the recorded retention evidence.
4. Stage 2 content, led by Docker-taught-from-this-app.
5. Design-only spike for the real lab runner per ADR-0005 (no
   implementation until the design review passes).

## Stop condition

Per master plan §36, v0.1 stops here. No real command execution, no Docker
sandboxes, no AI tutor, no Brain Core integration, no additional modules
beyond 0–3 were built. The next version should be driven by using this one.
