---
module: ssh
lesson: what-is-ssh
title: "SSH: A Shell on a Machine You Can't Touch"
difficulty: beginner
concepts:
  - ssh
  - remote-shell
prerequisites:
  - networking/ports-and-protocols
  - linux/processes-services-logs
quiz: ssh/what-is-ssh
flashcards:
  - card-ssh
  - card-sshd
---

## Why this matters

Your Lightsail host has no monitor and never will. Every command you've
practiced in this Lab's simulator — `ls`, `cd`, `chmod`, reading logs —
you'll eventually run on the real host *through SSH*. It is the
administration channel for effectively every Linux server on earth.

## Mental model

**Beginner mental model:** SSH gives you a terminal on a distant machine,
as if you'd plugged a keyboard into it — except the cable is encrypted
and can be thousands of miles long.

```
your laptop                    the Lightsail host
┌───────────┐   encrypted     ┌──────────────────┐
│ ssh client│ ──────────────▶ │ sshd (port 22)   │
│           │   TCP, port 22  │ → your shell     │
└───────────┘                 └──────────────────┘
```

**Technical reality:** SSH (Secure Shell) is a protocol. A daemon —
`sshd`, a service exactly as Module 1 defined — listens on port 22. Your
client connects (ordinary TCP, Module 2), the two sides negotiate
encryption, the server proves its identity, you prove yours, and then
sshd starts a shell *on the server* running *as your user there*, piping
its input/output through the encrypted channel. The commands execute
remotely; only keystrokes and text travel.

## Vocabulary

| Term | Plain meaning | Why you care |
|------|---------------|--------------|
| **SSH** | Encrypted remote-terminal (and file-transfer) protocol | How all server administration happens |
| **sshd** | The SSH daemon listening on the server, port 22 | The service that answers your connection |
| **remote shell** | A shell process running on the server, displayed on your machine | Everything you type runs *there*, as *that* user |
| **port 22** | SSH's well-known port | Why 22 is in every firewall discussion |

## Deep explanation

**The command.** `ssh ubuntu@203.0.113.7` means: connect to that host's
port 22, authenticate as the server-side user `ubuntu`, give me a shell.
From then on `pwd`, `ls`, `sudo systemctl status caddy` — all run on the
host. `exit` ends the remote shell; the server keeps running, exactly as
it was. (A surprisingly common beginner fear: closing SSH does *not*
stop the server — the services are daemons, not children of your
session.)

**Trust, both directions.** The first time you connect to a host, your
client shows a fingerprint and asks whether to trust it — this is the
server proving *its* identity, so nobody can silently impersonate your
machine later (details in the next lesson's `known_hosts`). Then *you*
authenticate: by password, or — as the next lesson insists — by key.

**Why port 22 is special-cased everywhere.** Every internet-facing
server is scanned constantly, and 22 is the most-knocked door: bots
trying common passwords around the clock. This is background radiation,
not a targeted attack — but it's why password login gets disabled
(next lesson), why some admins restrict 22 to their own IP, and why
your Lightsail firewall treats 22 differently from 80/443.

**More than a terminal.** The same channel carries file transfer
(`scp`, `sftp`) — and it's the transport your tools already use: when
git pushes to GitHub over `git@github.com:...`, that's SSH. When VS Code
or Claude Code operates on a remote machine, that's SSH too.

## Brain Core connection

Deploying Brain Core to any host is an SSH session: connect, `git pull`,
restart services, read logs. CI/CD systems that deploy automatically are
running the same SSH commands from a robot. Understanding the channel
means you can always fall back to hands-on-keyboard when automation
mystifies.

## Plex / home-server connection

A home server is usually headless in a closet. SSH from your laptop is
how you'll manage it — same protocol, private address instead of public.
(And when you're away from home, reaching it becomes a Module 2 journey
problem: private IP, port forwarding or VPN.)

## Interactive example

The prompt in this Lab's simulator — `learner@lab:~$` — is the classic
post-SSH prompt shape: *user* @ *host* : *where you are*. On real
multi-machine days, that prompt is what tells you which machine you're
about to run a command on. Misreading it is a classic incident cause.

## Practice

No exercise here — the next lesson's exercise covers the `~/.ssh`
directory hands-on. Instead, from memory, narrate what happens when you
run `ssh ubuntu@myhost` — connection, both identity checks, then what
you have. The quiz checks this narration.

## Common mistake

> Running a long task over SSH, closing the laptop, and finding the task
> dead.

The remote *shell* is your session; commands you launch normally belong
to it, and die with it (services managed by systemd/Docker don't — they
belong to the supervisor). The eventual tools are `tmux`/`screen` or
running things as services; for now, know the rule: your session's
children die with the session, daemons don't.

## Knowledge check

Quiz below.

## Summary

- SSH = an encrypted shell on a remote machine; commands run *there*.
- sshd is a daemon on port 22; the connection is ordinary TCP + crypto.
- Both sides authenticate: host fingerprint (their identity), then your
  password or key.
- Port 22 is scanned constantly everywhere — background radiation that
  shapes SSH hygiene.
- Closing SSH doesn't stop the server; your session's own child
  processes do die with it.
