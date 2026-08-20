---
module: docker
lesson: volumes-and-data
title: "Volumes: The Only Thing That Survives"
difficulty: beginner
concepts:
  - volume
  - bind-mount
  - container
prerequisites:
  - docker/images-and-containers
quiz: docker/volumes-and-data
exercise: docker/volume-disaster
flashcards:
  - card-volume-lifetime
  - card-volume-vs-bind
---

## Why this matters

There is one command in this whole module that can destroy real data,
and it differs from a routine one by two characters:

```
docker compose down       # containers gone, data safe
docker compose down -v    # containers gone, DATA GONE
```

This Lab's own compose file carries a comment about it. Task OS's
deployment notes say never to run it in production. You are about to
run it deliberately, in a simulation, and watch a database lose 1,200
orders — because that is the only way this ever becomes permanent
knowledge.

## Mental model

**Beginner mental model:** the container is a rented van. The volume is
your storage unit. You can swap vans as often as you like; the storage
unit is not part of the van.

```
   ┌───────────────────────────┐
   │ container  db             │
   │  /var/lib/postgresql/data ├──── mounted from ───┐
   │  /tmp/scratch             │  (dies with it)     │
   └───────────────────────────┘                     ▼
                                          ┌────────────────────┐
                                          │ volume  app_pgdata │
                                          │  outlives the      │
                                          │  container         │
                                          └────────────────────┘
```

**Technical reality:** a volume is storage that Docker manages, living
on the host under `/var/lib/docker/volumes/<name>/_data`, mounted into
the container at a path. Its lifetime is **independent** of every
container that ever mounts it. Removing containers does not touch it.
Only deleting the volume deletes it.

## Vocabulary

| Term | Plain meaning | Why you care |
|------|---------------|--------------|
| **volume** | Docker-managed storage referenced by name | Where data must live |
| **bind mount** | A host directory mapped into the container | How config and source get in |
| **`down -v`** | Down, *and delete the named volumes* | The data-loss flag |
| **mount point** | The path inside the container the storage appears at | Must match where the program actually writes |

## Deep explanation

**Two kinds of "storage into a container", and they are not
interchangeable.**

```yaml
volumes:
  - pgdata:/var/lib/postgresql/data     # named VOLUME — Docker owns it
  - ./content:/app/content:ro           # BIND MOUNT — your host directory
```

A **named volume** is portable, managed, and belongs to the machine. Use
it for data the application generates: databases, uploads, certificates.

A **bind mount** is a window onto a real host path. Its contents and
permissions are whatever the host has. Use it for things that come *from
outside*: configuration, source you are editing, read-only content. This
Lab mounts `./content` read-only (`:ro`) precisely so the application
cannot write to its own curriculum.

**Mount points must match where the program actually writes.** Mounting
a volume at `/var/lib/postgres/data` when Postgres writes to
`/var/lib/postgresql/data` produces a stack that starts, runs, appears
healthy — and stores everything in the writable layer, silently, until
the day you remove the container. There is no error. This class of bug
is only ever found by testing a restart.

**Why `down` and `down -v` both exist.** `down` is meant to be routine:
stop the stack, remove containers and networks, leave the data. `-v`
exists because volumes are otherwise immortal, and a machine that has
hosted twenty experiments accumulates twenty orphaned volumes. It is a
cleanup tool that happens to be one keystroke from your production
database. Muscle memory is the enemy here, which is why the real fix is
never typing it in a production directory at all.

**Certificates are data too.** The Caddy on your server keeps its
Let's Encrypt certificates and ACME account key in the `caddy_data`
volume. Lose it and Caddy re-issues from scratch — straight into
Let's Encrypt's rate limits, which can lock the domain out for days.
That volume is not "just cache"; it is state.

## Brain Core connection

Brain Core's provenance chain — claim to measurement to assay to sample
— is only trustworthy if it is durable. A provenance database in a
container's writable layer is worse than no provenance database,
because it looks authoritative right up to the moment it disappears.
Volume first, schema second.

## Plex / home-server connection

Plex's metadata — watch history, artwork, what you rated — lives in its
config directory. In a container that path *must* be a volume or bind
mount, or a routine Plex upgrade wipes years of viewing history. The
media itself is normally a bind mount of a big disk; the config is the
part people forget.

## Interactive example

In the exercise, run this sequence and watch carefully:

```
docker compose up -d
docker exec shop-db-1 ls /var/lib/postgresql/data     # orders.tbl is there
docker compose down
docker compose up -d
docker exec shop-db-1 ls /var/lib/postgresql/data     # still there
docker compose down -v
docker compose up -d
docker exec shop-db-1 ls /var/lib/postgresql/data     # empty
```

The cache container in the same stack has no volume. Watch what happens
to *its* data after the very first `down`.

## Practice

Exercise: **The volume disaster**. You will lose the data on purpose,
then prove you can tell — from the compose file alone — which services
would survive.

## Common mistake

> Running `docker compose down -v` to "get a clean start" when a
> container will not come up.

It usually does fix the symptom, which is exactly why it becomes a
habit. Then one day the failing container is the database, the volume
you delete holds the only copy of production data, and the same reflex
that has worked twenty times destroys it. Reach for `down` and
`up -d --force-recreate` first; `-v` is for scratch stacks you can
name out loud as disposable.

## Knowledge check

Quiz below.

## Summary

- A volume's lifetime is independent of any container. That is the
  entire point.
- `docker compose down` keeps named volumes; `down -v` deletes them.
- Data with no volume lives in the container's writable layer and dies
  with it — silently, and usually later than you would notice.
- Named volumes are for data the app generates; bind mounts are for
  config and source coming from the host.
- A mount point that does not match where the program writes fails
  silently and looks healthy.
