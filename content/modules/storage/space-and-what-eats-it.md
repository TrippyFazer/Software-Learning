---
module: storage
lesson: space-and-what-eats-it
title: "The Disk Is Full: The Drill"
difficulty: beginner
concepts:
  - disk-usage
  - inode
  - filesystem-format
prerequisites:
  - storage/disks-partitions-filesystems
quiz: storage/space-and-what-eats-it
exercise: storage/disk-is-full
flashcards:
  - card-df-vs-du
  - card-deleted-but-open
  - card-inode
---

## Why this matters

A full disk does not produce one clear error. It produces a database
that will not accept writes, a web server returning 500s, logs that stop
being written *just as you go to read them*, and a package manager that
refuses to help. Everything fails at once, confusingly, and the cause is
one number.

This is the single most common real incident on a small server, and it
has a fixed drill. Learn the drill and it becomes a five-minute
annoyance instead of an evening.

## Mental model

**Beginner mental model:** `df` tells you *that* you have a problem.
`du` tells you *where* it is. Always in that order — top down, never
guessing.

```
df -h                    →  "/ is 98% full"          WHICH filesystem
du -h /var | sort        →  "/var/log is 61G"        WHICH directory
du -h /var/log | sort    →  "app.log is 60G"         WHICH file
ls -lh /var/log/app.log  →  confirm before deleting  ARE YOU SURE
```

**Technical reality:** `df` asks the *filesystem* for its own
accounting — fast, authoritative, one number per mount. `du` walks the
directory tree adding up files — slow, and it can only see files that
still have a name.

That difference is the source of the most confusing storage bug there
is, below.

## Vocabulary

| Term | Plain meaning | Why you care |
|------|---------------|--------------|
| **`df`** | Free space per filesystem | Tells you *that* |
| **`du`** | Space used per directory | Tells you *where* |
| **inode** | The record holding a file's metadata and block pointers | You can run out of these while space remains |
| **deleted-but-open** | A file unlinked while a process still holds it | Space stays used until that process closes it |

## Deep explanation

**Start at the top and narrow.** `du -h /` on a full disk takes minutes
and prints thousands of lines. Instead, descend one level at a time:
`du -h --max-depth=1 /`, pick the big number, descend into it. Three or
four steps finds anything. The usual culprits, roughly in order:
runaway logs, an old backup nobody rotated, Docker images and stopped
containers, a database that grew, and a core dump.

**`df` and `du` disagree, and `df` is right.** If `du` says 12 GB is
used and `df` says 60 GB, the difference is almost always a
**deleted-but-open** file. Unlinking a file removes its *name*; the data
survives while any process still has it open. `du` walks names, so it
cannot see it. `df` asks the filesystem, which is still holding the
blocks. Deleting a giant log while the application has it open frees
nothing at all — you must restart (or signal) the process that holds it.
This catches everybody once.

**You can be full with space free.** A filesystem has a fixed number of
**inodes**, one per file. Millions of tiny files — session files, cache
entries, one-file-per-message queues — can exhaust the inode table while
`df -h` still shows gigabytes available. The symptom is "No space left
on device" with plenty of space; the tell is `df -i`.

**On this server, specifically.** `/` is 77 GB and holds: two
PostgreSQL databases, every Docker image and layer, both applications'
containers, and `~/backups`. Docker is the usual suspect — old images
accumulate silently with every rebuild. `docker system df` shows what
Docker is holding, and `docker image prune` reclaims dangling layers.
But note the standing rule for this machine: **never** casually run
`docker system prune` or `docker volume prune`. Those reach past images
and can take volumes — which is to say, databases.

**The backups are on the same disk.** `~/backups` grows nightly on the
same 77 GB it is protecting. That is a real dependency: a full disk
stops the backups too, silently, at exactly the moment you would most
want a recent one.

## Brain Core connection

Document ingestion is a disk-growth engine: originals, extracted text,
chunks, embeddings — several copies of the same information by design.
A retention policy decided early ("originals kept, intermediates
regenerable") is much cheaper than one improvised during an outage.

## Plex / home-server connection

Media servers fill disks as a matter of routine. The specific home-lab
trap is transcoding: temporary files can be tens of gigabytes, and the
default location is often the OS disk rather than the big array. A Plex
box that dies weekly at exactly the wrong moment is usually a transcode
directory pointed at the wrong filesystem.

## Interactive example

In the exercise, run `df -h` first and look at `Use%`. Then narrow with
`du`. Then delete the culprit and run `df -h` again — and watch the
number actually move. That last step is the one people skip, and it is
the only proof the problem is fixed.

## Practice

Exercise: **The disk is full**. A web application has stopped
responding. You get a shell and `df`. Find it, fix it, confirm it.

## Common mistake

> Deleting a huge log file, seeing `df` unchanged, and concluding the
> disk is broken.

The application still has the file open. The name is gone; the blocks
are not. Restart the service (or use its log-rotation signal) and the
space appears instantly. The real fix is log rotation configured *before*
it happens — which, on this server, is the `max-size`/`max-file` policy
in `/etc/docker/daemon.json` that caps every container's logs.

## Knowledge check

Quiz below.

## Summary

- `df` says *that* you are full; `du` says *where*. Always in that
  order, narrowing top-down.
- When they disagree, believe `df` — the gap is a deleted-but-open file
  held by a running process.
- Inodes can run out while space remains. `df -i`.
- On a Docker host, images and stopped containers are a prime suspect —
  but `system prune` and `volume prune` reach further than you want.
- Confirm the fix by re-running `df`. Anything less is a guess.
