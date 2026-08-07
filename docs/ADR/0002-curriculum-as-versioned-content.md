# ADR-0002: Curriculum is version-controlled content, not code or database rows

Status: Accepted · Date: 2026-08-07

## Context

Lessons could live (a) hardcoded in React components, (b) as rows in
PostgreSQL behind an editing UI, or (c) as structured files in git.

## Decision

Curriculum lives in `content/` as **Markdown with YAML frontmatter** (plus
YAML files for quizzes, exercises, flashcards, and module manifests). The
API parses and validates it at startup into an in-memory content index; the
frontend receives it through read-only API endpoints.

Learner *state* (attempts, mastery, progress) references content by stable
slug and lives in PostgreSQL (ADR-0003).

## Consequences

- Authoring a lesson = writing a file + git commit. Diffable, reviewable,
  revertible; no CMS to build or secure.
- Content deploys atomically with code; a content typo can't be "hotfixed"
  into divergence from the repo.
- Invalid content fails at load time with a precise error (module, file,
  field), not at request time.
- Slugs are contracts: renaming a concept slug orphans mastery rows, so
  renames require a documented migration step.
- A future AI tutor may *generate supplements* but never writes into
  `content/` — the canonical curriculum stays human-versioned.
