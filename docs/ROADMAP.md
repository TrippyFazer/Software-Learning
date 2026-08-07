# Roadmap

## v0.1 — the walking skeleton that teaches (CURRENT)

Success definition: open `https://learn.example.com`, log in securely, see
the curriculum, complete a lesson, learn vocabulary, answer questions, use
the simulated Linux terminal, make mistakes safely, complete a challenge,
leave, return later, and see progress preserved.

In scope:

- Authentication (single learner, Argon2id, server-side sessions)
- Dashboard, curriculum map, module navigation, lesson pages
- Concept vocabulary, quiz engine, attempt tracking, basic mastery
- Flashcards (simple review, history preserved for future SRS)
- Simulated terminal framework + state-evaluated exercises
- Modules 0–3 with representative lessons
- Stage 1 boss challenge (SERVER ROOKIE)
- Progress dashboard, responsive UI
- Lightsail deployment, backups, security posture

Explicitly **out** of v0.1 (do not build spontaneously):

- Real command execution / Docker sandboxes
- AI tutor
- Brain Core integration
- Modules 4–30 content
- Multi-user, organizations, social, billing
- Sophisticated spaced-repetition scheduling
- Analytics beyond the progress dashboard

## v0.2 candidates — chosen by *using* v0.1, not by speculation

After dogfooding, `V0_1_STATUS.md` records what actually helped and hurt.
Likely candidates, to be validated against real use:

1. **Real lab runner (design in ADR-0005).** Web app → Lab API → dedicated
   runner → ephemeral isolated environments. Strict CPU/RAM/process/time
   limits, non-root, no privileged mode, no host filesystem, no secrets,
   no outbound network, fresh per session, auto-cleanup. Evaluate rootless
   Docker vs Podman vs microVMs at that time.
2. **Spaced review scheduler** on top of the preserved attempt history
   (start with something as simple as SM-2 buckets).
3. **More simulator commands** (`grep`, `find`, `chmod`, `chown`, `ps`,
   `df`, `du`, `free`) and richer failure scenarios.
4. **Stage 2 content** (Storage, Hardware, Plex, Proxmox, Docker) — the
   Docker module can teach from this app's own compose file.
5. **AI tutor (supplement only).** Explains wrong answers, generates
   examples, detects weak concepts. Canonical curriculum stays in git;
   AI output is never persisted as curriculum.

## Future: Brain Core connector (design only)

A narrow, outbound-only boundary through which the Lab can publish learning
state, e.g.:

```
POST <brain-core>/api/knowledge-assertions
{ "subject": "Tripp", "predicate": "UNDERSTANDS", "object": "docker-volume",
  "confidence": 0.83, "evidence_url": ".../progress/docker-volume" }
```

Rules: Learning Lab must remain fully usable if Brain Core is down; the
connector is fire-and-forget with retry, no inbound dependency; nothing in
the Lab schema references Brain Core. Not implemented in v0.1.

## Non-goals (any version)

Kubernetes, Kafka, microservices, graph databases, vector databases (unless
a retrieval module genuinely needs a local one for teaching), multi-tenant
SaaS features. The architecture stays understandable — that's the product.
