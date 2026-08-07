# ADR-0003: PostgreSQL stores learner state only

Status: Accepted · Date: 2026-08-07

## Context

With curriculum in git (ADR-0002), the database's job must be defined
precisely, and the temptation to mirror content into tables resisted.

## Decision

PostgreSQL stores exactly the mutable, per-learner facts: users, sessions,
attempts (append-only), mastery records, flashcard review state, lesson
progress, learning sessions, and login attempts. Content is referenced by
slug strings — there are **no** `modules`/`lessons`/`questions` tables.

Schema is managed by Alembic migrations. Attempts are append-only so that a
future spaced-repetition scheduler has full history to work from.

## Consequences

- Dropping the DB loses progress but never curriculum; restoring a backup
  restores everything the git repo doesn't already contain.
- No referential integrity between DB and content — accepted trade-off,
  mitigated by load-time content validation and a startup check that logs
  mastery rows referencing unknown slugs.
- Deliberately not over-normalized: slug strings instead of lookup tables,
  JSONB for answer payloads and VFS snapshots. PostgreSQL's relational
  power is used where it earns its keep (attempt queries, progress
  aggregation), not everywhere it could be.
