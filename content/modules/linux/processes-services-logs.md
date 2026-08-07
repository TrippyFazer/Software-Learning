---
module: linux
lesson: processes-services-logs
title: "Processes, Services, and Logs: Seeing What a Server Is Doing"
difficulty: beginner
concepts:
  - process-management
  - daemon
  - log
prerequisites:
  - linux/users-and-permissions
quiz: linux/processes-services-logs
exercise: linux/read-the-logs
flashcards:
  - card-daemon
  - card-log
  - card-var-log
---

## Why this matters

A server with a problem doesn't show a dialog box. It *stops answering* —
and the only way to find out why is to look at what's running (processes),
what's supposed to be running (services), and what happened (logs). This
triad is the diagnostic loop you'll use for every failure, including this
stage's boss challenge.

## Mental model

**Beginner mental model:**

- **Processes** — what is running *right now* (Module 0 introduced these).
- **Services** — processes with a contract: start at boot, stay up,
  restart on failure.
- **Logs** — the diary every well-behaved service keeps: timestamped lines
  saying what it did and what went wrong.

Think of a clinical trial: processes are what's happening in the lab
today; the protocol says what *should* be happening (services); and the
lab notebook (logs) is where you reconstruct what actually occurred when
results look wrong. Diagnosis without logs is guesswork.

**Technical reality:** on modern Linux, a supervisor called **systemd**
starts services from unit files, restarts them per policy, and captures
their output. `ps` lists processes; `systemctl status <service>` asks the
supervisor; `journalctl` and files under `/var/log` hold the history. (In
Docker deployments like this Lab, the docker daemon plays the supervisor
role and `docker compose logs` reads the diary — same concepts, different
tooling.)

## Vocabulary

| Term | Plain meaning | Why you care |
|------|---------------|--------------|
| **daemon** | A background service process (the `d` in `sshd`, `systemd`) | The word appears constantly in server docs |
| **log** | Timestamped record of what a program did | The primary evidence in every diagnosis |
| **/var/log** | The conventional directory for system and service logs | Where you look first |
| **exit / crash** | A process ending — voluntarily or not | A "down" service is a process that ended and didn't restart |

## Deep explanation

**The diagnostic loop.** When "the app is down," the questions run in
order:

1. **Is the process running?** (`ps`, or `systemctl status app`,
   or `docker compose ps`.) If not — it crashed or never started.
2. **What did it say before it stopped?** Read the log. Services almost
   always announce their reason for dying: a missing file, a permission
   error, a port already in use, a database it couldn't reach.
3. **Fix the cause, restart, watch the log again.** A service that
   crashes on startup will usually tell you the same thing louder.

**Reading logs.** Log lines follow a loose grammar: timestamp, severity
(`INFO`, `WARNING`, `ERROR`), message. Practical skills: read from the
*end* backwards (the last error before the silence is usually the cause);
distinguish the routine noise from the anomaly; and trust specific
messages — `cannot connect to database on port 5432` is a gift, not
jargon.

**Why services die, in practice.** The same handful of causes covers most
real incidents: a file or directory it needs is missing or unreadable
(permissions!); its port is already taken; a dependency (like the
database) isn't up; the disk is full; or its configuration has a typo.
Notice that you already have the tools for several of these.

## Brain Core connection

Brain Core's backend will be a service with logs, and you've already seen
its future shape: this Lab's API logs one structured JSON line per request.
When Brain Core misbehaves at 11pm, your loop will be: is the container
up? (`docker compose ps`) → what do the logs say? (`docker compose logs
api`) → fix, restart, re-watch. Identical to today's lesson.

## Plex / home-server connection

"Plex won't start after the update" — is the process running? What does
its log say (Plex keeps logs in its data directory)? The forum-post ritual
of "turn it off and on again" works occasionally; the log tells you *why*,
every time.

## Interactive example

The exercise gives you a `/var/log` with a web application's log in it.
`cat` is your log reader here (real servers add `tail`, `grep`, and
`journalctl` — later lessons).

## Practice

Mission: **Read the Logs.** A web application died. The log knows why.
Find the cause and record your answer as instructed in the mission text.

## Common mistake

> Restarting a crashed service over and over, hoping.

If a service died for a *reason* — missing config, bad permissions, port
conflict — restarting reproduces the crash exactly. The log already
contains the reason, usually in its final ERROR lines. The habit: **read
the log before the third restart.** Restart-first is only correct for
genuinely transient causes, and the log is how you know whether the cause
was transient.

## Knowledge check

Quiz below.

## Summary

- Processes are what runs now; services are processes with a stay-up
  contract; logs are the record.
- The diagnostic loop: is it running? → what did the log say? → fix,
  restart, watch.
- Logs live under `/var/log` (or `docker compose logs` here); read from
  the end backward.
- Most service deaths have mundane causes: files, permissions, ports,
  dependencies, disk.
- Read the log before the third restart.
