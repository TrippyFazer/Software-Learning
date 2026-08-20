---
module: hardware
lesson: when-a-machine-runs-out
title: "When a Machine Runs Out"
difficulty: intermediate
concepts:
  - oom-killer
  - swap
  - memory-limit
prerequisites:
  - hardware/cpu-and-memory
  - docker/compose-files
quiz: hardware/when-a-machine-runs-out
flashcards:
  - card-oom
  - card-swap
  - card-memlimit
---

## Why this matters

Running out of CPU is a bad afternoon. Running out of memory is an
outage with no error message in your application's logs — because your
application was not given the chance to log anything. It was killed
mid-instruction.

Recognising this failure by its *shape* is the difference between ten
minutes and a whole evening.

## Mental model

**Beginner mental model:** when the kernel cannot find memory for
something it must do, it picks a process and kills it. There is no
negotiation and no warning.

```
  memory pressure rises
        │
        ├── swap available?  ──▶ push idle pages to disk (slow, survivable)
        │
        └── nothing left     ──▶ OOM killer picks a victim
                                  (usually the biggest, which is usually
                                   the thing you care about most)
```

**Technical reality:** the **OOM killer** scores processes by memory
footprint and a few heuristics, then kills the worst offender. In
`docker ps` this shows as a container that "restarted for no reason". In
`journalctl` or `dmesg` it shows as an explicit line naming the victim.
Your application's own logs show nothing at all, because SIGKILL cannot
be caught.

## Vocabulary

| Term | Plain meaning | Why you care |
|------|---------------|--------------|
| **OOM killer** | Kernel process-killer of last resort | The cause of "it just restarted" |
| **swap** | Disk used as slow overflow memory | Buys survival, costs speed |
| **memory limit** | A cap on one container's memory | Bounds the blast radius |
| **exit code 137** | Killed by SIGKILL (128 + 9) | The fingerprint of an OOM kill |

## Deep explanation

**How to recognise it.** A container disappears and comes back.
`docker ps` shows a recent uptime you did not cause. `docker inspect`
reports **exit code 137** — 128 plus signal 9. Nothing useful in the
application log, because there was no shutdown. On the host,
`journalctl -k | grep -i oom` names the victim outright.

**Swap changes the failure, not the arithmetic.** Swap lets the kernel
move idle pages to disk instead of killing something, which converts a
hard failure into a slow one. That is usually the trade you want on a
small server: a sluggish minute beats a dead database. But swap on a
cloud volume is *orders of magnitude* slower than RAM, and a machine
that is actively swapping its working set is effectively down anyway —
it just takes longer to admit it.

**Limits contain damage; they do not create memory.** `mem_limit: 512m`
on the API does not make the machine bigger. It guarantees that a
leaking API is killed *before* it starves PostgreSQL and Caddy. That is
the whole argument: a bounded failure in one application instead of an
unbounded one across the machine. And it is exactly why the shared Caddy
has no limit — the blast radius there is every site at once.

**Builds are the usual culprit on small machines.** Compiling a
frontend bundle is a spike of pure CPU and memory on a box that is
otherwise idle. On 3.7 GB shared with two running applications, an
uncapped Node build can take the whole machine down while doing
something that is not even production work — which is why the Dockerfile
pins `--max-old-space-size=768`. A build that fails cleanly is far
better than a build that kills the database.

**The honest fixes, in order.** Find the leak. Cap the offender. Add
swap so failures are slow rather than sudden. Move the heavy job off the
box. Buy a bigger machine. In that order — because "buy more RAM" as a
first response just moves the same leak to a larger machine and a bigger
bill.

## Brain Core connection

Ingestion is the risk: parsing a large PDF, chunking it and embedding
the chunks can hold a lot at once, and it is easy to write a loop that
accumulates instead of streaming. On a shared box that is not a slow
job, it is an outage for everything else. Cap the worker, stream rather
than accumulate, and let it be slow.

## Plex / home-server connection

Home servers usually have more RAM and much more variable load. The
equivalent trap is a transcode plus a library scan plus a backup all
starting at once because they are all scheduled at 3am. Stagger them.
The machine's capacity is not the sum of what it can do overnight; it is
what it can do *simultaneously*.

## Interactive example

On the real host, these two answer "how close am I?":

```
free -h                # is `available` shrinking over days?
docker stats --no-stream
```

`docker stats` shows each container's memory against its limit. A
container sitting at 95% of its limit is not healthy; it is one busy
request away from exit code 137.

## Practice

Covered by the previous lesson's exercise, where you choose limits for a
stack that has to fit in this machine.

## Common mistake

> Raising a container's memory limit because it keeps getting killed.

Sometimes right — the limit was genuinely too small. Often it converts a
contained failure into a machine-wide one: the container stops dying and
starts starving everything else instead, and now the *database* is the
victim. Look at the trend first. A limit that was fine for months and is
not now usually means a leak, and the leak is the thing to fix.

## Knowledge check

Quiz below.

## Summary

- Out of memory means the kernel kills a process. No warning, no
  application log.
- **Exit code 137** is the fingerprint; `journalctl -k | grep -i oom`
  names the victim.
- Swap converts a sudden failure into a slow one. It does not add
  capacity.
- Limits bound the blast radius to one application — which is why the
  shared proxy has none.
- Raising a limit is sometimes the fix and sometimes just moving the
  victim.
