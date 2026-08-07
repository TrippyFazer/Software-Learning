# Deployment — AWS Lightsail runbook

Target: an Ubuntu 24.04 LTS Lightsail instance serving
`https://learn.example.com` via Docker Compose + Caddy.

```
Internet → DNS → Lightsail static IP → Caddy (:443) → Docker network → web/api → PostgreSQL
```

Every step below is meant to be understood, not just pasted — the Networking
and SSH modules of the curriculum explain what each one does.

## 0. Prerequisites

- A Lightsail instance (≥1 GB RAM works; 2 GB is comfortable), Ubuntu 24.04.
- A **static IP** attached to the instance (Lightsail → Networking).
- A domain with an `A` record: `learn.example.com → <static IP>`.
- Your SSH public key registered with the instance.

## 1. First login and non-root administration

Lightsail's default user is `ubuntu` (already non-root with sudo). Use it —
do not enable root SSH login.

```bash
ssh -i ~/.ssh/your-key ubuntu@<static-ip>
```

Harden SSH (`/etc/ssh/sshd_config` or a drop-in in `sshd_config.d/`):

```
PasswordAuthentication no
PermitRootLogin no
```

```bash
sudo systemctl restart ssh
```

Keep your current session open until you've confirmed a new key-based login
works in a second terminal.

## 2. Firewall — both layers

**Lightsail firewall** (console → instance → Networking): allow only
SSH (22), HTTP (80), HTTPS (443). Optionally restrict 22 to your IP.

**On-instance ufw** (defense in depth):

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

PostgreSQL and uvicorn are never exposed; they exist only on the internal
Docker network, so no firewall rule for them should ever be added.

## 3. System updates

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades   # enable security auto-updates
```

## 4. Install Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu     # log out/in afterwards
docker --version && docker compose version
```

(Adding `ubuntu` to the `docker` group is root-equivalent for that user —
acceptable here because `ubuntu` already has sudo; don't add other users.)

## 5. Deploy the repository

```bash
sudo mkdir -p /srv/learning-lab && sudo chown ubuntu:ubuntu /srv/learning-lab
cd /srv/learning-lab
git clone <your-repo-url> .
```

## 6. Configure environment

```bash
cp .env.example .env
nano .env
```

Set at minimum:

- `APP_ENV=production`
- `PUBLIC_HOSTNAME=learn.example.com`
- `POSTGRES_PASSWORD` — long random string
- `SESSION_SECRET` — `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`
- `BOOTSTRAP_USER_EMAIL` / `BOOTSTRAP_USER_PASSWORD`

Then set the real domain in `infra/docker/Caddyfile` (replace
`learn.example.com` if different). Caddy will obtain TLS certificates
automatically the first time it starts — DNS must already point at the
instance for this to succeed.

## 7. First start

```bash
docker compose up -d --build
docker compose ps                      # all services healthy?
curl -fsS http://localhost:8000/api/health   # from inside: docker compose exec api curl ...
```

Apply migrations and create the learner account:

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m scripts.create_user
```

Visit `https://learn.example.com` — you should see the login page over
HTTPS with a valid certificate.

## 8. PostgreSQL persistence

Database files live in the named Docker volume `pgdata`
(`docker volume inspect learning-lab_pgdata`). Containers can be removed
and rebuilt freely; the volume persists. **Never** run
`docker compose down -v` on production — the `-v` deletes volumes.

## 9. Updates (application)

```bash
cd /srv/learning-lab
git pull
docker compose up -d --build           # rebuilds changed images, restarts
docker compose exec api alembic upgrade head   # if migrations changed
docker image prune -f                  # reclaim old layers
```

Content-only changes (files under `content/`) need only
`git pull && docker compose restart api`.

## 10. Backups

Nightly database dump (learner state; the curriculum is already in git):

```bash
./scripts/backup_db.sh        # writes backups/learninglab-YYYYMMDD-HHMMSS.sql.gz
```

Install as a cron job:

```bash
crontab -e
# 03:15 UTC nightly
15 3 * * * cd /srv/learning-lab && ./scripts/backup_db.sh >> backups/backup.log 2>&1
```

Copy backups off the instance periodically (e.g. `scp` to your workstation
or a Lightsail bucket). A backup that exists only on the server it backs up
is half a backup.

## 11. Restore

```bash
./scripts/restore_db.sh backups/learninglab-YYYYMMDD-HHMMSS.sql.gz
```

The script restores into the running postgres container (dropping and
recreating the schema). **Verification:** `scripts/restore_db.sh` supports
`--target <dbname>` to restore into a scratch database first; the test
procedure (restore latest backup into `learninglab_restore_test`, count
rows, drop it) is the required proof before trusting the pipeline. The repo's
test suite also exercises dump/restore against a disposable database.

## 12. Log inspection

```bash
docker compose logs -f api            # structured JSON app logs
docker compose logs -f caddy          # access + TLS logs
docker compose logs --since 1h postgres
journalctl -u docker --since today    # docker daemon itself
```

## 13. Monitoring (manual, v0.1)

```bash
df -h /                                # disk — keep >20% free
docker system df                       # what docker is consuming
docker compose ps                      # health checks
docker compose exec postgres psql -U learninglab -c "SELECT pg_size_pretty(pg_database_size('learninglab'));"
curl -fsS https://learn.example.com/api/health
```

If disk fills: `docker image prune -a -f`, clear old `backups/*.gz` after
copying them off, check `docker compose logs` sizes (json-file log rotation
is configured in compose).

## 14. Troubleshooting

| Symptom | First checks |
|---------|--------------|
| Site unreachable | DNS resolves to static IP? Lightsail firewall 80/443 open? `docker compose ps` |
| TLS errors | Caddy logs — ACME needs DNS pointing here and port 80 reachable |
| 502 from Caddy | api container healthy? `docker compose logs api` |
| Login fails after redeploy | migrations applied? `SESSION_SECRET` unchanged? |
| DB connection refused | postgres healthy? correct `POSTGRES_*` in `.env`? |

Nothing in this runbook automates destructive changes; every `down -v`,
`prune`, or restore is a deliberate manual step with its effect stated.
