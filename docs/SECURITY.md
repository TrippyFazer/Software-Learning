# Security

This application is internet-accessible. This document is the threat model,
the hard rules, and the operational security posture.

## Threat model (proportionate)

Single-user private app; the assets are the learner's progress data and —
far more importantly — **the host itself**, which may later run other
services. The realistic threats are:

1. Internet-wide scanning/exploitation of exposed services
2. Credential stuffing / brute-force on the login form
3. A vulnerability in the app being used to run commands on the host
4. Secrets leaking through git or logs
5. Data loss through operator error

Threat 3 dominates the design: the app *teaches* a terminal, so the
temptation to "just execute it for real" is the primary standing danger.

## Hard rules

| # | Rule | Enforced by |
|---|------|-------------|
| 1 | No learner input is ever executed on the host. The terminal is a pure simulation. | No `subprocess`/`os.system`/`eval`/`exec`/`pty` in the simterm module; tests in `apps/api/tests/test_simterm_safety.py` scan for these imports and prove commands mutate only an in-memory VFS |
| 2 | No Docker socket mounted into web/api containers | `docker-compose.yml` review; nothing mounts `/var/run/docker.sock` |
| 3 | API container runs as non-root | `USER app` in `infra/docker/api.Dockerfile` |
| 4 | PostgreSQL never published to the internet | No `ports:` mapping on the postgres service; internal Docker network only |
| 5 | No secrets in git | `.gitignore` blocks `.env*` (except `.env.example`); placeholders only |
| 6 | HTTPS everywhere in production | Caddy automatic TLS; HTTP→HTTPS redirect |
| 7 | Sessions: opaque server-side tokens, HttpOnly + Secure + SameSite=Lax cookies, expiring, revocable | `modules/auth/` |
| 8 | Passwords: Argon2id | `argon2-cffi` via `modules/auth/security.py` |
| 9 | Login rate limiting + temporary lockout | `LoginAttempt` tracking, configurable via env |
| 10 | All API input validated | Pydantic models on every endpoint |

## Exposed ports — the complete list

On the Lightsail instance, exactly three ports are open:

| Port | Protocol | Why | Restriction |
|------|----------|-----|-------------|
| 22   | TCP | SSH administration | Key-only auth; consider restricting source IP in the Lightsail firewall |
| 80   | TCP | ACME challenges + redirect to HTTPS | Served by Caddy only |
| 443  | TCP | The application | Served by Caddy only |

Everything else is closed at **both** the Lightsail firewall and `ufw` on the
instance (defense in depth). PostgreSQL (5432) and uvicorn (8000) are
reachable only on the internal Docker network.

## Authentication design

- Email + password login; single learner account created by an operator
  script (no self-registration endpoint).
- Argon2id password hashing (library defaults; documented in code).
- On login: random 256-bit token generated; **only its SHA-256 hash is
  stored**; token set in an HttpOnly, SameSite=Lax cookie (Secure when
  `APP_ENV=production`).
- Sessions expire after `SESSION_TTL_HOURS`; logout deletes the server-side
  record (real revocation, not just cookie clearing).
- Rate limiting: after `LOGIN_MAX_ATTEMPTS` failures within
  `LOGIN_WINDOW_SECONDS`, logins for that account are refused for
  `LOGIN_LOCKOUT_SECONDS`. Failures are logged.
- Deliberately **no** OAuth/SSO and **no** localStorage JWTs (ADR notes:
  cookie sessions are simpler, revocable, and XSS-resistant).

## Secure headers

Caddy sets: `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`,
and a restrictive `Content-Security-Policy` (self-only scripts/styles; no
inline script). The SPA renders lesson Markdown without raw-HTML
pass-through, so lesson content cannot inject markup.

## Simulated terminal — why it is safe

The "terminal" is a text protocol against an in-memory data structure:

```
learner input → our tokenizer → command handlers → virtual filesystem (dict tree)
```

- There is no shell process anywhere in the path.
- The simterm module has no imports capable of process execution; a test
  asserts this by inspecting the module source and its import graph.
- A test feeds hostile inputs (`; rm -rf /`, `$(reboot)`, backticks, path
  traversal to `/etc/passwd`) and asserts the host filesystem is untouched
  and the VFS responds as a naive filesystem would.
- Worst case of a simulator bug: a corrupted *virtual* filesystem for one
  learner. Blast radius ends at a JSON blob.

## Future real lab runner (v0.2+) — security boundary, design only

Real command execution, when it comes, will NOT run in or beside the web
app. Design (ADR-0005): web app → Lab API → **dedicated runner** →
disposable isolated environments with strict CPU/RAM/process/time limits,
non-root, no privileged mode, no host filesystem, no production secrets, no
Docker socket exposure to the web app, restricted/disabled outbound network,
fresh per session, auto-cleanup. Rootless Docker vs Podman vs microVMs to be
evaluated *then*. Nothing in v0.1 implements any of this.

## Operational security

- **Updates:** `docs/DEPLOYMENT.md` documents OS patching and image updates.
- **Backups:** nightly `pg_dump` via `scripts/backup_db.sh`; restore
  procedure documented and verified against a scratch database
  (`scripts/restore_db.sh`).
- **Logs:** structured API logs (no passwords, no session tokens logged);
  Caddy access logs; inspection commands documented in DEPLOYMENT.md.
- **Dependencies:** lockfiles committed (`uv.lock`, `package-lock.json`);
  update cadence documented in DEPLOYMENT.md.
- **About This Server page:** shows conceptual architecture only — no
  internal IPs, no versions beyond what headers reveal anyway, no secrets.

## Reporting

Single-user app: if something looks compromised, rotate `SESSION_SECRET`
and the database password, revoke sessions (`TRUNCATE sessions;`), rebuild
containers from a clean pull, and restore data from the last good backup.
