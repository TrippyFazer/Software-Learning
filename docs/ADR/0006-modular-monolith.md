# ADR-0006: Modular monolith

Status: Accepted · Date: 2026-08-07

## Context

The app must be operable by one learner on one small instance, and its
architecture is itself course material (Module 10). Microservices would
demonstrate distributed systems the learner isn't ready to operate;
an unstructured monolith would demonstrate nothing.

## Decision

One FastAPI process, internally split into modules with explicit ownership:

- `auth` — identity, sessions, rate limiting
- `content` — read-only curriculum loading/validation from `content/`
- `learning` — attempts, mastery, flashcards, progress
- `simterm` — virtual filesystem + command interpreter (pure, no I/O)

Rules: modules interact only through each other's public service functions
(no reaching into another module's tables or internals); `simterm` stays a
pure library with no database or network access of its own; `content` never
writes anywhere.

## Consequences

- Single deployable, single database, trivial local dev — while still
  giving the learner real examples of boundaries, ownership, and layering.
- If a piece ever genuinely needs extraction (the lab runner will —
  ADR-0005), the module seam is where it cuts.
- Discipline is enforced socially (review + CLAUDE.md) and by tests, not by
  process isolation. Accepted at this scale.
