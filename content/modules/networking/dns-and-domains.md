---
module: networking
lesson: dns-and-domains
title: "DNS: Names for Numbers"
difficulty: beginner
concepts:
  - dns
  - domain
prerequisites:
  - networking/addresses-and-networks
quiz: networking/dns-and-domains
flashcards:
  - card-dns
  - card-domain
  - card-a-record
---

## Why this matters

You'll buy a domain, point `learn.example.com` at a Lightsail IP, and
later point more names at more services. DNS is a ten-minute concept that
people fumble for years because they never learn what's actually being
looked up, by whom, and when. It's also the first suspect whenever "the
site is down" but the server is fine.

## Mental model

**Beginner mental model:** DNS is the internet's phone book. Humans use
names (`learn.example.com`); connections need numbers (`203.0.113.7`);
DNS translates, one direction, on demand.

**Technical reality:** DNS is a distributed, delegated database. No single
phone book exists; instead, authority is delegated down the name:
the root knows who runs `.com`; `.com`'s servers know who is
*authoritative* for `example.com`; that authoritative server holds the
actual **records**. Your machine asks a *resolver* (usually your ISP's or
1.1.1.1 / 8.8.8.8), which walks that chain and then **caches** the answer
for the record's TTL (time-to-live).

## Vocabulary

| Term | Plain meaning | Why you care |
|------|---------------|--------------|
| **domain** | A name you lease the rights to (`example.com`) and can hang subdomains off | Your services' permanent identity |
| **DNS** | The system translating names to IP addresses | First suspect in "site unreachable" |
| **A record** | "This name → this IPv4 address" | The record you'll set for learn.example.com |
| **TTL** | How long resolvers may cache an answer | Why DNS changes "take time to propagate" |
| **resolver** | The server that does lookups for you and caches results | Where stale answers live |

## Deep explanation

**What you'll actually do.** In your DNS provider's control panel, you
create an A record: `learn.example.com → <your Lightsail static IP>`.
Minutes later (TTL-dependent), the world's resolvers can find your
server. Subdomains are free structure: `learn.`, `brain.`, `plex.` — many
names, one domain, possibly many servers or one.

**Caching explains the weirdness.** DNS answers are cached at multiple
layers (your OS, your router, the resolver). So: changes appear at
different times for different people ("works on my phone, not my
laptop"); a *lowered* TTL before a planned move makes cutovers fast; and
a dead cached answer can outlive a fixed server. When DNS is the
suspect, the question is always *whose cache is stale?*

**What DNS is not.** It doesn't route traffic, check whether the server
is up, or handle ports. It answers exactly one question — "what address
is this name?" — and then leaves. If the name resolves correctly and the
site is still down, DNS is innocent; move down the stack (next lesson).

**Names decouple identity from location.** Because clients connect to
*names*, you can move a service to a new host, update one A record, and
every client follows. This is the same indirection trick you'll meet
throughout software (APIs, interfaces): stable name, movable
implementation.

## Brain Core connection

Brain Core will get its own name (`brain.yourdomain.com`) the same way
this Lab got `learn.example.com`. Because both are just A records, they
can point at the same host today and different hosts next year — the
migration plan is "change a record," not "re-configure every client."

## Plex / home-server connection

Home servers meet DNS twice: friendly names for LAN services (via local
DNS or your router), and — if you self-host anything externally —
*dynamic* DNS, which re-points a name at your home's public IP whenever
your ISP changes it. Same records, updated by a robot.

## Interactive example

On **About This Server**, the DNS node sits between you and the static
IP. Note what that placement means: the lookup happened *before* any
connection to the server — DNS failure looks like "server down" even
when the server is perfectly healthy.

## Practice

Trace it manually: pick any domain you use. Ask yourself which parts are
the domain, the subdomain, and what record must exist for it to work.
(On your own machine later: `nslookup` or `dig` will show you real
answers and TTLs.)

## Common mistake

> "I updated the DNS record but the site still goes to the old server.
> The update didn't work."

It almost certainly did — but the *old* answer, with its TTL, is still
cached somewhere between you and the authority. Patience (or a
lower-TTL-in-advance strategy, or flushing your local cache) is the fix.
Check from a device on a different network before concluding anything.

## Knowledge check

Quiz below.

## Summary

- DNS translates names to addresses via delegated authority + caching.
- An A record (`name → IPv4`) is what points learn.example.com at your host.
- TTL-based caching explains propagation delays and stale answers.
- DNS neither routes nor health-checks; resolving ≠ reachable.
- Names decouple identity from location — move hosts by changing a record.
