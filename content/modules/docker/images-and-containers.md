---
module: docker
lesson: images-and-containers
title: "Images and Containers: Template and Instance"
difficulty: beginner
concepts:
  - image
  - container
  - layer
  - registry
prerequisites:
  - linux/processes-services-logs
  - systems/anatomy-of-an-application
quiz: docker/images-and-containers
exercise: docker/lifecycle
flashcards:
  - card-image-vs-container
  - card-container-not-vm
  - card-layer-cache
  - card-tag-pinning
---

## Why this matters

Two applications run on your Lightsail host right now — this Lab and
Task OS — and neither one was "installed" on it. Nothing was
`apt install`ed. There is no Postgres on the host, no Python, no
Node. Yet a PostgreSQL 16 and a PostgreSQL 17 are both running,
happily, with different versions, and neither can see the other.

That is the thing Docker actually buys you, and it is worth
understanding before the syntax.

## Mental model

**Beginner mental model:** an *image* is a frozen template — an install
disc. A *container* is one running copy of it. One disc, many machines.

```
      image: postgres:16              (read-only, on disk once)
              │
    ┌─────────┼─────────┐             docker run
    ▼         ▼         ▼
 container container container        (three separate running processes,
   "db1"    "db2"     "db3"            each with its own scratch space)
```

**Technical reality:** an image is a stack of read-only filesystem
layers plus metadata — the default command, the ports it expects, the
environment. A container is an ordinary Linux **process on the host
kernel** (Module 1's definition of process, unchanged), given three
kinds of isolation:

- its own **filesystem view**: the image's layers, plus one thin
  writable layer on top, which is the only part it can change
- its own **network namespace**: its own interfaces and its own idea of
  which ports are in use
- its own **process tree**: inside, its main process is PID 1

**A container is not a virtual machine.** A VM boots a whole guest
kernel on virtual hardware — gigabytes, tens of seconds. A container
borrows the host's kernel and starts in milliseconds. This is why
`docker ps` on your server shows seven containers on a machine with
3.7 GB of RAM, and why that is unremarkable.

## Vocabulary

| Term | Plain meaning | Why you care |
|------|---------------|--------------|
| **image** | Frozen template: filesystem + default command | What you pull and run |
| **container** | One running instance of an image | What actually serves traffic |
| **layer** | One cached step of the build | Why build order matters |
| **registry** | The server images are pulled from | `postgres:17-alpine` is a download instruction |
| **tag** | A moving label on an image (`:16`, `:latest`) | Pinning it is how you avoid surprise upgrades |

## Deep explanation

**The writable layer is the whole trap.** Everything a container writes
that is not on a volume (next lesson) lands in that thin top layer, and
that layer is deleted with the container. Not "moved to a bin" —
deleted. This is a *feature*: it is what makes containers disposable,
what lets you `docker compose up -d` after a change and get a clean
machine. It is also why a database with no volume loses everything the
first time you tidy up.

**Layers are cached, in order.** Look at this Lab's own API image:

```dockerfile
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev   # ← dependency layer
COPY . .                                             # ← source layer
```

Dependencies are installed *before* the source is copied. Change one
line of Python and only the last layers rebuild; the dependency install
is reused from cache. Reverse those two lines and every code edit
re-downloads every package. The build would still be *correct* — just
slow enough that you would stop rebuilding, which is its own kind of
broken.

**Tags move; digests do not.** `postgres:16` today and `postgres:16`
next year are different bytes — 16.2 versus 16.9, say. That is usually
what you want (security patches). `postgres:latest` is a different
proposition: it means *whatever was pushed most recently*, which one
day is PostgreSQL 18, and your data directory from 17 will not start
under it. Task OS pins `postgres:17-alpine`. Caddy pins `caddy:2.11-alpine`.
That is deliberate: patches arrive automatically, major versions never
arrive by surprise.

**Containers are cattle, and the naming shows it.** `docker ps` on your
host lists `task-os-api`, `learning-lab-postgres` — names given
explicitly. Without a name, Docker generates one, because the
expectation is that you will delete it shortly and make another.

## Brain Core connection

Brain Core will need a database, an API, probably a vector store and a
worker. Each becomes an image; each runs as a container; the versions
are pinned in one file. When you move it to a bigger machine, you move
the file, not a two-page list of install steps that has drifted from
what is actually on the server.

## Plex / home-server connection

A Plex home server is usually a stack of containers: Plex itself, maybe
a downloader, an indexer, a reverse proxy. Each is an image with a
version tag. Upgrading Plex becomes: change the tag, `up -d`, and if it
misbehaves, change the tag back. Try that with a package manager.

## Interactive example

In the exercise below, run `docker images` and then `docker ps -a`.
Notice that the image list barely changes while containers come and go.
That asymmetry — few images, many disposable containers — *is* the
mental model.

## Practice

Exercise: **The container lifecycle**. Pull an image, run two
containers from it, stop one, remove it, and observe what happened to
the image. Check the goals as you go.

## Common mistake

> "I installed the Python packages inside the running container and now
> they are gone."

`docker exec` into a container, `pip install` something, and it works —
until the container is replaced, which is routine. The change lived in
the writable layer. Anything that must persist belongs in the image (so
it is rebuilt every time) or on a volume (so it outlives the
container). Nothing you type inside a running container is durable.

## Knowledge check

Quiz below.

## Summary

- An image is a read-only template; a container is a running instance
  with one thin writable layer. One image, many containers.
- A container is a **process on the host kernel**, not a virtual
  machine — no guest OS, milliseconds to start.
- The writable layer dies with the container. That is the feature and
  the trap.
- Layers are cached in order: install dependencies before copying
  source, or every code edit rebuilds the world.
- Tags move. Pin the version line you intend to run; `latest` is a
  promise to surprise you.
