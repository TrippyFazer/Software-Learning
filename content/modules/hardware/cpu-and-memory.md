---
module: hardware
lesson: cpu-and-memory
title: "Reading a Spec Sheet: CPU and Memory"
difficulty: beginner
concepts:
  - vcpu
  - core-vs-thread
  - ram
  - page-cache
prerequisites:
  - linux/processes-services-logs
quiz: hardware/cpu-and-memory
exercise: hardware/size-the-limits
flashcards:
  - card-vcpu
  - card-buff-cache
  - card-cpu-vs-io
---

## Why this matters

Your server is a **t3.medium: 2 vCPU, 3.7 GB RAM, 77 GB disk**. Those
three numbers already decided several things you have seen: why the
frontend build caps its heap, why every container carries a `mem_limit`,
why Caddy deliberately does *not*, and why the architecture notes say
"no Redis, no Elasticsearch, no message broker".

A spec sheet is not trivia. It is the budget every later decision is
spent against.

## Mental model

**Beginner mental model:** CPU is *how fast work gets done*. RAM is *how
much work can be in progress at once*. Running out of them fails in
completely different ways: too little CPU is **slow**, too little RAM is
**dead**.

```
   2 vCPU        ── work in progress ──▶   queue gets longer, everything slows
   3.7 GB RAM    ── work in progress ──▶   the kernel kills something
```

**Technical reality:** a **core** is a physical execution unit. A
**thread** (hyper-threading / SMT) is a second instruction stream
sharing one core's machinery — real gains on stalls, but not a second
core. A **vCPU** on most cloud providers is *one thread*, not one core.

So "2 vCPU" on this instance is **one physical core with two threads**.
`lscpu` says so directly: `Thread(s) per core: 2`, `Core(s) per socket: 1`.
That is why the deployment notes describe this as "a 1-physical-core
host" and why the API runs 2 uvicorn workers rather than 8.

## Vocabulary

| Term | Plain meaning | Why you care |
|------|---------------|--------------|
| **core** | A physical execution unit | The real unit of parallel work |
| **thread / SMT** | A second instruction stream on one core | Why 2 vCPU ≠ 2 cores |
| **vCPU** | What the cloud sells you — usually one thread | The number on the invoice |
| **RAM** | Working memory; volatile | Running out kills processes |
| **buff/cache** | RAM the kernel is using as a disk cache | Looks used, is reclaimable — read `available` instead |

## Deep explanation

**Read your own machine.** Three commands:

```
nproc        how many vCPUs the kernel sees
lscpu        cores, threads per core, model
free -h      memory: total, used, buff/cache, available
```

**`free` is the most misread output on Linux.** People see `used` at
1.5 GB and `free` at 200 MB and panic. But a large `buff/cache` is the
kernel doing its job: keeping recently-read disk blocks in otherwise
idle RAM, and handing that memory straight back the moment a program
wants it. **`available` is the number that matters** — it is the
kernel's own estimate of how much a new process could get. Unused RAM is
wasted RAM.

**CPU-bound versus I/O-bound.** Most web work is I/O-bound: waiting on a
database, a disk, a network. Waiting costs almost no CPU, which is why
two vCPUs can serve a great many idle requests. What actually saturates
this machine is *CPU-bound* work — compiling a frontend bundle, building
a Docker image, generating embeddings, transcoding video. Those do not
queue politely; they take everything.

**Where the specs are visible in this deployment:**

- `NODE_OPTIONS=--max-old-space-size=768` in the frontend build stage.
  Node's default heap on a small machine can balloon past what is
  available while two other applications are running. Capping it makes
  the build fail *predictably* instead of taking the machine down.
- `mem_limit` on the API, worker and database containers: a bounded
  blast radius, so one leaking application cannot starve the others.
- **No `mem_limit` on Caddy**, deliberately. Caddy is the front door for
  every site; if it were OOM-killed, everything would go dark at once.
  Limits belong where the blast radius is one app.
- Two uvicorn workers, not eight. More workers on one physical core do
  not add throughput; they add context switching and memory.

## Brain Core connection

Embedding generation is CPU-bound and memory-hungry — the opposite of
serving web requests. Running it on the same 2 vCPU box that serves the
UI means ingestion competes directly with responsiveness. The eventual
answer is a queue and a worker that can be throttled, or a bigger
machine for that job. Knowing *which kind* of work you are adding is how
you predict that before it hurts.

## Plex / home-server connection

Plex is the clearest case of "specs decide architecture". Direct play
costs almost nothing. Transcoding 4K in software will pin every core you
own. Hardware transcoding (Intel Quick Sync) moves it to a dedicated
block on the CPU, and turns an impossible workload into an idle one.
That is a *hardware* answer to a software problem, and it is why people
choose specific CPUs for media boxes.

## Interactive example

In the exercise, run `nproc` and then `lscpu`. Notice that `nproc` says
2 and `lscpu` says one core with two threads. Both are true; they answer
different questions, and only one of them predicts how much parallel
work this machine can really do.

## Practice

Exercise: **Size the limits**. Read the machine, then choose memory
limits for a stack and write them into its compose file.

## Common mistake

> Reading `free -h`, seeing 200 MB "free", and concluding the server is
> out of memory.

`free` is not `available`. The kernel had filled idle RAM with cache and
will release it instantly on demand. The line worth watching is
`available` — and, when things are genuinely tight, whether swap is
being touched.

## Knowledge check

Quiz below.

## Summary

- Too little CPU is slow; too little RAM is fatal. Different failures,
  different fixes.
- A vCPU is usually one **thread**. This machine's 2 vCPU is one
  physical core.
- In `free`, read **`available`**, not `free` — buff/cache is
  reclaimable.
- I/O-bound work waits cheaply; CPU-bound work (builds, transcodes,
  embeddings) saturates everything.
- Memory limits belong where the blast radius is one application, never
  on the shared front door.
