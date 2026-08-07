# ADR-0005: Security boundary for the future real lab runner

Status: Accepted (design only — nothing implemented) · Date: 2026-08-07

## Context

Eventually the learner should run *real* commands in *real* disposable
environments (v0.2+). The dangerous default would be to grow the existing
API into an executor — mounting the Docker socket, spawning containers
beside the web app. That collapses the trust boundary that ADR-0004
established.

## Decision (binding on future work)

Real execution gets its **own trust zone**:

```
Web application → Lab API (narrow, authenticated) → Dedicated Lab Runner
                                                       → ephemeral isolated environment
```

Non-negotiable properties of the runner, whatever technology is chosen:

- Environments are disposable: fresh per session, auto-cleanup after.
- Strict limits: CPU, RAM, process count, execution timeout, disk quota.
- Non-root inside the sandbox; never `--privileged`.
- No host filesystem access; no production secrets present in the sandbox.
- The web/api containers never get the Docker socket — the runner is
  reached only through the Lab API.
- Outbound network from sandboxes disabled or tightly restricted.

Technology evaluation (rootless Docker vs Podman vs gVisor/microVMs, and
same-host vs separate instance) is explicitly deferred until v0.2 planning,
against the requirements above.

## Consequences

- v0.1 contains zero real-execution code paths, so there is nothing to
  accidentally expose.
- The Lab API contract can be designed against the simulator's exercise
  format, keeping content forward-compatible.
- Cost: real labs may eventually need a second (or beefier) instance.
  Accepted — isolation is the point.
