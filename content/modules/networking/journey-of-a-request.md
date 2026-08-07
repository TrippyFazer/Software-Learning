---
module: networking
lesson: journey-of-a-request
title: "What Happens When You Type learn.example.com?"
difficulty: beginner
concepts:
  - firewall
  - reverse-proxy
  - bandwidth-latency
prerequisites:
  - networking/ports-and-protocols
quiz: networking/journey-of-a-request
flashcards:
  - card-firewall
  - card-reverse-proxy
  - card-bandwidth-latency
---

## Why this matters

This lesson assembles the whole module into one story — the actual story
of how this page reached you. It's the classic systems interview
question, but more importantly it's the *diagnostic map*: when something
breaks, the failure lives at one specific step, and knowing the sequence
tells you where to look.

## Mental model

**The journey, end to end:**

```
You type learn.example.com and press Enter
  1. DNS      → the name becomes an IP address
  2. TCP      → your browser connects to that IP, port 443
  3. TLS      → certificate checked; the pipe is encrypted
  4. Firewall → the packet was allowed in (443 is open; most ports aren't)
  5. Caddy    → the reverse proxy receives the request
  6. Routing  → /api/* goes to the backend; everything else = frontend files
  7. Backend  → FastAPI checks your session cookie, does the work
  8. Database → PostgreSQL answers the backend's queries
  9. Response → back through the same chain, in reverse
```

Nine steps, each with its own failure signature. This *is* the About
This Server diagram, told as a sequence.

## Vocabulary

| Term | Plain meaning | Why you care |
|------|---------------|--------------|
| **firewall** | The bouncer: rules for which ports/sources may connect | Why the database is unreachable from the internet — on purpose |
| **reverse proxy** | The single front door that terminates TLS and routes inward | Caddy here; nginx elsewhere; the pattern is everywhere |
| **bandwidth** | How much data per second the pipe carries | Streaming quality, backup duration |
| **latency** | How long one round trip takes | Snappiness; unfixable by more bandwidth |

## Deep explanation

**The firewall (step 4)** examines every arriving packet against rules:
allow TCP 443 from anywhere, allow 22, drop everything else. Dropped
traffic gets no reply — to a port scanner, closed ports look like
silence. Your Lightsail host has two layers (the cloud firewall and
`ufw` on the instance) — redundancy on purpose, because one
misconfiguration shouldn't equal exposure.

**The reverse proxy (step 5)** exists so that *one* hardened process
faces the internet. Caddy terminates TLS (holding the certificates),
sets security headers, and routes by path: `/api/*` → the backend on
its internal port 8000; anything else → static files. The backend never
faces the internet directly. This pattern — many internal services, one
front door — repeats at every scale from this Lab to companies with
thousands of servers.

**Bandwidth vs latency (the response's physics).** Bandwidth is pipe
*width* — megabits per second. Latency is pipe *length* — milliseconds
per round trip, floor-bounded by distance and the speed of light. They
fail differently: low bandwidth makes big transfers slow (4K streams
stutter); high latency makes *interactions* laggy (every click waits a
round trip) no matter how wide the pipe. A satellite link can have huge
bandwidth and painful latency; a LAN has modest bandwidth and sub-
millisecond latency. Diagnosing "it's slow" starts by asking which one
you're feeling.

**Failure signatures, by step.** Name doesn't resolve → DNS (step 1).
Timeout → firewall drop or dead host (step 4 / wrong IP). Connection
refused → nothing listening (step 5 down). Certificate warning → TLS
(step 3). 502 Bad Gateway → proxy up, backend down (step 7). 500 →
backend bug. Slow → bandwidth, latency, or an overloaded step 7/8. One
symptom, one primary suspect — this table is most of practical network
debugging.

## Brain Core connection

Brain Core's request journey will be *identical* — same DNS, same TLS,
same reverse proxy pattern, same internal-only database. Design decisions
you'll face (should the vector service be internet-reachable? does the
GPU box need a public port?) are all "who gets past step 4" questions.

## Plex / home-server connection

Remote Plex streaming is this journey pointed at your house: DNS (or
Plex's relay) finds your public IP, your router's firewall must allow
port 32400 through (that's "port forwarding" — a home firewall rule),
and bandwidth/latency decide whether 4K survives the trip. Every remote-
access guide you'll read is steps 1–4 with Plex vocabulary.

## Interactive example

Open **About This Server** and walk the diagram top to bottom, narrating
each hop from this lesson. Then, in your browser's dev tools (F12 →
Network), reload and click any request: you can see the status code and
timing — the journey's receipt.

## Practice

For each symptom, name the step (answers in the quiz): a certificate
warning; a 502 error; a name that won't resolve; a connection that hangs
then times out; a page that loads but every click feels delayed by half
a second.

## Common mistake

> "The site is slow — we need more bandwidth."

Maybe. But if the pages are small and the *interactions* lag, the
problem is latency (or a slow backend), and a bigger pipe changes
nothing. Conversely, buffering video with snappy clicks is bandwidth.
Naming which resource is scarce *before* spending money is exactly the
systems thinking this curriculum is building.

## Knowledge check

Quiz below.

## Summary

- The journey: DNS → TCP → TLS → firewall → reverse proxy → backend →
  database → back.
- Firewalls allow-list ports; dropped packets look like silence; this
  host runs two firewall layers on purpose.
- A reverse proxy gives many internal services one hardened front door;
  the backend and database never face the internet.
- Bandwidth = pipe width (transfers); latency = pipe length
  (interactions); they fail differently.
- Each failure symptom points at one step — debug by walking the chain.
