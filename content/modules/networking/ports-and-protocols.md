---
module: networking
lesson: ports-and-protocols
title: "Ports, TCP, and the HTTP Family"
difficulty: beginner
concepts:
  - port
  - tcp
  - http
  - https
prerequisites:
  - networking/dns-and-domains
quiz: networking/ports-and-protocols
flashcards:
  - card-port
  - card-tcp
  - card-http
  - card-https
---

## Why this matters

An IP address finds the *machine* — but the machine runs many programs.
Ports find the *program*. Every "connection refused," every firewall
rule, every `:8000` in a URL, and every security review you'll ever do
speaks the language of ports and protocols.

## Mental model

**Beginner mental model:** a port is a numbered door into a server. The
machine has thousands of doors; each listening program stands behind one.
Mail slots at one street address: same building (IP), different
recipients (ports).

**Technical reality:** a TCP or UDP port is a 16-bit number (0–65535)
that, combined with an IP address, identifies one communication endpoint.
A server program *listens* on a port; a client connects to
`address:port`. Nothing about a port is physical — it's bookkeeping in
the OS's networking layer, which hands arriving data to whichever
process claimed that number.

## Vocabulary

| Term | Plain meaning | Why you care |
|------|---------------|--------------|
| **port** | Numbered endpoint on a host; one listening program per port | connection = IP + port, always |
| **TCP** | The reliable transport: ordered, complete delivery over a connection | What HTTP, SSH, and databases ride on |
| **HTTP** | The request/response protocol of the web | The language your browser and this Lab's API speak |
| **HTTPS** | HTTP inside TLS encryption | Confidentiality + integrity + proof of who you're talking to |
| **well-known port** | Conventional numbers: 22 SSH, 80 HTTP, 443 HTTPS, 5432 PostgreSQL | How you read firewall rules and error messages at a glance |

## Deep explanation

**TCP** gives programs a clean illusion: a two-way pipe where bytes
arrive complete and in order, over a network that actually loses and
reorders packets constantly. It does this with acknowledgments and
retransmission. (Its sibling UDP skips the guarantees for speed —
streaming and games.) When a connection is *refused*, TCP is telling you
precisely: the machine answered, and nothing is listening on that port.
Distinguish this from a *timeout* — nothing answered at all (wrong
address, or a firewall silently dropping you). These two errors point in
different directions and you'll meet both.

**HTTP** rides on TCP: the client sends a request (`GET /api/health`),
the server sends a response (status code + body). Status codes are a
taxonomy worth absorbing early: 2xx success, 3xx redirect, 4xx *you*
made a mistake (404 not found, 401 not authenticated), 5xx *the server*
broke. You've already generated several of each using this Lab.

**HTTPS** wraps the whole HTTP conversation in TLS: encrypted (nobody in
between can read it), integrity-checked (nobody can alter it), and
authenticated (a certificate proves you reached the real
`learn.example.com`, which is what Caddy obtains automatically for this
Lab). The padlock means the *pipe* is safe — it says nothing about
whether the site itself is trustworthy.

**Conventions.** 80 is where browsers expect plain HTTP, 443 HTTPS, 22
SSH, 5432 PostgreSQL. Nothing enforces this — you could run a web server
on 5432 — but conventions are shared expectations, and firewall rules,
URLs (`:8000` overrides the default), and error messages all assume you
know the famous numbers.

## Brain Core connection

Brain Core's architecture will be described in ports: its API on 8000
behind a proxy on 443, PostgreSQL on 5432 *not* exposed, maybe a vector
service somewhere — and its security review will be one question asked
repeatedly: *which ports are reachable from where?* You can already
answer that question for the Lab you're using (three, and you know them).

## Plex / home-server connection

Plex Media Server listens on port 32400 — the number appears in every
Plex networking guide, port-forwarding rule, and "remote access not
working" thread. LAN clients connect straight to `server-ip:32400`;
remote access is precisely the art of getting outside traffic to that
port safely.

## Interactive example

In your browser's address bar, this Lab is port 443 (implied by
`https://`). On **About This Server**, count the ports in the diagram:
443 public, 8000 internal (Caddy → API), 5432 internal (API →
PostgreSQL). Same machine, three doors, only one facing the street.

## Practice

From memory, write down what lives on: 22, 80, 443, 5432. Then explain —
in one sentence each — why this Lab exposes exactly three of them (the
SECURITY.md table has the answer to check against).

## Common mistake

> "The site's down." — but `https://myserver` loads a *different* page
> than expected, or "connection refused" appears after a deploy.

Beginners treat the server as one reachable/unreachable blob. The port
model splits the question: DNS resolved? TCP connected on 443? Something
listening there? Right thing listening? Each failure has a distinct
symptom (bad name / timeout / refused / wrong content). Diagnosing by
layers, in order, replaces guessing — the boss challenge will lean on
this.

## Knowledge check

Quiz below.

## Summary

- Port = 16-bit number; IP finds the machine, port finds the program.
- TCP fakes a reliable pipe over an unreliable network; refused ≠
  timeout, and the difference is diagnostic gold.
- HTTP is request/response with status codes (2xx/3xx/4xx/5xx); HTTPS is
  HTTP inside TLS with certificate-proven identity.
- Well-known ports (22/80/443/5432) are conventions everyone reads
  fluently.
- Security reviews start with: which ports, reachable from where?
