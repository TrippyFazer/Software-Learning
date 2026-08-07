# ADR-0004: Simulated terminal before real command execution

Status: Accepted · Date: 2026-08-07

## Context

Terminal practice is the heart of the curriculum, but a web app that
executes learner shell commands on its own host is a standing catastrophe:
this host is internet-facing and will later sit near other services. Even
"restricted" real shells (allowlists, chroots, containers-beside-the-app)
have a long history of escapes, and v0.1 has no capacity to operate them
safely.

## Decision

v0.1 ships a **pure simulation**: an in-memory virtual filesystem (a Python
tree structure, JSON-serializable) and a hand-written interpreter for an
educational command set (`pwd ls cd mkdir touch cat cp mv rm echo whoami`,
growing as lessons need). Learner input never reaches a shell, `subprocess`,
or the host filesystem.

Exercises are graded against the **resulting VFS state**, not the typed
command strings, so equivalent solutions pass (`mkdir a && cd a` vs
`mkdir a; cd a` vs creating things in a different order).

Enforcement is tested: `test_simterm_safety.py` (a) asserts the simterm
module's import graph contains no process-execution capability, and
(b) feeds hostile input (command injection, `$(...)`, backticks, path
traversal) and asserts the host is untouched.

## Consequences

- Worst-case bug = corrupted virtual state for one learner, fixable by
  reset. Blast radius ends at a JSON blob.
- The simulator will always lag real Linux (no pipes, globbing, or job
  control initially). Accepted: fidelity grows lesson-by-lesson, and the
  gap is itself taught ("the real shell also does X").
- Real execution is deferred to a dedicated, isolated lab runner with its
  own trust boundary (ADR-0005) — not an evolution of this simulator's
  deployment position.
