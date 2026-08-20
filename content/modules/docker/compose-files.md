---
module: docker
lesson: compose-files
title: "Compose: One File That Describes a Machine"
difficulty: intermediate
concepts:
  - compose
  - compose-service
  - volume
  - port-publishing
prerequisites:
  - docker/volumes-and-data
  - docker/networks-and-ports
quiz: docker/compose-files
exercise: docker/fix-the-stack
flashcards:
  - card-compose-declarative
---

## Why this matters

You can now read the file that defines this application. Not a
simplified teaching version — the real one, running on the real server,
right now. That is the point of this module: the deployment is the
curriculum.

## Mental model

**Beginner mental model:** a compose file is a description of the
machine you want, not a list of steps. You hand it to Docker and say
"make it look like this."

**Technical reality:** Compose is **declarative** and **convergent**.
`up -d` compares what the file says to what is running and changes only
the difference. Running it twice is safe. A container already matching
its spec is left alone — which is why the deploy command on this server
is `docker compose up -d --no-deps api`, and why it does not interrupt
the database.

## Vocabulary

| Term | Plain meaning | Why you care |
|------|---------------|--------------|
| **service** (Compose) | One named role in the stack — "the database" | Becomes a DNS name; produces containers. Not Module 1's `service` (a long-running process); a Compose service is a *declaration* that produces one. |
| **project** | The stack's name, prefixing everything it creates | Why `name:` should always be explicit |
| **`depends_on`** | Ordering, and optionally health gating | The difference between "started" and "ready" |
| **`restart: unless-stopped`** | Restart on failure and at boot — but not if you stopped it deliberately | What brings the server back after a reboot |

## Deep explanation

**Read this Lab's own file.** Three services:

```yaml
name: learning-lab            # explicit: never guessed from the directory

services:
  caddy:      # the only service with ports:
  api:
    expose: ["8000"]          # internal only — see the previous lesson
    depends_on:
      postgres:
        condition: service_healthy
  postgres:
    volumes: [pgdata:/var/lib/postgresql/data]
    # deliberately NO ports:
volumes:
  pgdata:
```

Everything you have learned is visible in it: one published door, a
named volume for the only stateful service, an internal-only API, and
an explicit project name.

**`name:` is not cosmetic.** Without it, Compose derives the project
name from the *directory*, so container and volume names depend on
where the file happens to sit. Move or rename the folder and
`docker compose down` stops finding the stack it created — you now have
orphans with names you must discover. One line prevents it.

**`depends_on` has two very different meanings.** Plain `depends_on:
[postgres]` only orders *starting*. The API will launch the moment
Postgres's process exists, which is several seconds before Postgres
accepts connections — so the API crashes on its first query, restarts,
and eventually succeeds, leaving a confusing burst of errors in the
logs at every boot. `condition: service_healthy` waits for the
**healthcheck** to pass. That is the difference between "started" and
"ready", and it is worth the extra three lines every time.

**Healthchecks should not lie.** Task OS's API healthcheck deliberately
does not touch the database: it answers "is this process alive". Had it
queried Postgres, a brief database blip would mark the API unhealthy,
restart it, and turn a five-second hiccup into a restart storm across
the whole web tier. A healthcheck answers one narrow question; make
sure you know which.

**Override files: adapting a stack you do not own.** Compose
automatically merges `docker-compose.override.yml` on top of
`docker-compose.yml`. This Lab arrived assuming it owned the whole
machine — its own Caddy publishing 80 and 443. On a shared host those
ports belong to the central Caddy. The fix was an override, not an
edit:

```yaml
services:
  caddy:
    ports: !reset []        # `ports: []` alone would NOT work
    networks: [default, proxy]
```

`!reset` matters: Compose merges sequences **additively**, so an empty
list leaves the inherited ports in place. And the override is kept out
of git locally, so `git pull` never conflicts. The general rule: when
you must adapt an application you do not maintain, add a layer — never
edit the file upstream will change.

**Always verify the merge.** Do not assume:

```
docker compose config          # the fully merged, final spec
```

## Brain Core connection

Brain Core's compose file will *be* its deployment documentation.
Anyone reading it learns the whole shape: what runs, what is public,
what is stateful, what depends on what. Written well, it replaces a
wiki page that would have gone stale within a month.

## Plex / home-server connection

A home media stack is usually six or seven services. Compose turns
"rebuild my home server" from a weekend of remembering into: restore
the file, restore the volumes, `up -d`. That is only true if the file
is under version control and the volumes are backed up. Neither is
automatic.

## Interactive example

Run `docker compose config` in the exercise to see the merged result,
then `docker compose ps` to see what it produced. The gap between those
two outputs — desired versus actual — is exactly what `up` closes.

## Practice

Exercise: **Fix the stack**. A compose file has three defects, each one
covered by a lesson in this module. Find them by reading, prove them by
running.

## Common mistake

> `docker compose down` to restart an application.

`down` removes containers *and the network*, taking the whole stack
offline including the database — for what was meant to be a code
deploy. The narrow tool is `docker compose up -d --no-deps <service>`:
rebuild and replace one service, leave everything else running. This
server's operations notes say "never `down`" for exactly this reason.

## Knowledge check

Quiz below.

## Summary

- Compose is declarative and convergent: `up -d` changes only the
  difference, and is safe to run twice.
- Set `name:` explicitly, or your container and volume names depend on
  a directory name.
- `depends_on` alone orders startup; `condition: service_healthy` waits
  for readiness. They are not the same.
- A healthcheck should answer one narrow question — a database check in
  a web healthcheck turns a blip into a restart storm.
- Adapt stacks you do not own with an override file, and verify the
  result with `docker compose config`.
