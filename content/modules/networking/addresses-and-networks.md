---
module: networking
lesson: addresses-and-networks
title: "Addresses and Networks: LAN, WAN, and IP"
difficulty: beginner
concepts:
  - ip-address
  - lan
  - wan
  - router
  - public-private-ip
prerequisites:
  - systems/what-is-a-server
quiz: networking/addresses-and-networks
flashcards:
  - card-ip
  - card-lan-wan
  - card-router
  - card-public-private
---

## Why this matters

Your Plex server will live on a home network. Your Lightsail host lives on
AWS's network. Brain Core's pieces will talk across networks constantly.
"Why can't X reach Y" is one of the two eternal infrastructure questions
(the other is permissions, and you've met it) — and it always starts with
addresses.

## Mental model

**Beginner mental model:** an IP address is a postal address for a
computer. A **LAN** (local area network) is your building's internal mail
system — fast, private, yours. The **WAN** (wide area network — in
practice, the internet) is the global postal service. The **router** is
the mailroom in the lobby connecting the two.

**Technical reality:** an IPv4 address is 32 bits written as four numbers
(`203.0.113.7`). Certain ranges — `192.168.x.x`, `10.x.x.x`,
`172.16-31.x.x` — are reserved for **private** use: every home and office
reuses them internally, and the internet refuses to route them. Your
machines have private addresses; your router holds the one **public**
address, and rewrites traffic between the two (NAT). IPv6 exists to make
addresses abundant, but IPv4 + NAT is still what you'll mostly operate.

## Vocabulary

| Term | Plain meaning | Why you care |
|------|---------------|--------------|
| **IP address** | A computer's network address | The target of every connection |
| **LAN** | Your local, private network | Where your Plex clients and server find each other |
| **WAN** | The wide network beyond your router — the internet | Where your Lightsail host lives |
| **router** | The device connecting LAN to WAN, translating addresses | Why "my IP" means two different numbers |
| **public / private IP** | Internet-routable vs internal-only address ranges | The #1 confusion in home networking |

## Deep explanation

**Two views of "my address."** Ask your laptop its IP and it says
something like `192.168.1.42` — its private LAN address, assigned by your
router. Ask a website "what's my IP" and it reports your router's
*public* address. Both answers are true; they're addresses on different
networks. Your laptop is not directly reachable from the internet — the
router stands in front of it, which is both why home devices survive
being online and why *hosting* things from home requires extra steps
(port forwarding — next lessons).

**Your Lightsail host is different on purpose.** A rented cloud host gets
(or is attached to) a public IP: directly reachable from anywhere. That's
what makes it a useful place to serve from — and why its firewall
matters so much more than your laptop's (Module 22 will return to this).

**Reachability reasoning.** "Can X talk to Y?" decomposes into: are they
on the same LAN (then usually yes, directly)? Is Y public (then yes,
across the WAN)? Is Y private and X outside (then no — not without the
router's explicit help)? Most home-server head-scratching resolves to
this triage.

## Brain Core connection

Early Brain Core will run on a public cloud host (like this Lab). If you
later move pieces home — a GPU box, a storage node — the public/private
split becomes a design decision: what's reachable from where, and through
what? You'll draw exactly this lesson's diagram, with your own boxes.

## Plex / home-server connection

Plex works on the LAN out of the box: server `192.168.1.50`, TV
`192.168.1.60`, same network, direct connection. *Remote* streaming (your
phone on cellular) crosses the WAN into your private LAN — which is why
it needs Plex's relay service or deliberate router configuration, and
why it sometimes mysteriously "works at home but not at Grandma's."

## Interactive example

On the **About This Server** page: the "Lightsail static IP" node is a
public address; everything below it (the Docker network) is a private
network *inside* the host — the same public/private pattern, one level
deeper. Networks nest.

## Practice

No terminal exercise — the simulator has no network yet. Instead: find
your own laptop's private IP (OS network settings) and your network's
public IP (any "what is my IP" site). Confirm they differ, and explain to
yourself why both are correct.

## Common mistake

> "My server's IP is 192.168.1.50 — I'll give that to my friend so they
> can reach it."

`192.168.*` addresses exist in *every* home network — your friend's
network has its own `192.168.1.50` (possibly their printer). Private
addresses only mean something inside their own LAN. Anything you share
externally must be a public address — plus, as the next lessons show, a
port and ideally a name.

## Knowledge check

Quiz below.

## Summary

- IP addresses are the postal addresses of networking; IPv4 is four
  numbers, `203.0.113.7`.
- LAN = your private network; WAN = the internet; the router bridges and
  translates between them (NAT).
- `192.168.*`, `10.*`, `172.16-31.*` are private: reused everywhere,
  unroutable on the internet.
- Home machines hide behind the router's one public IP; cloud hosts wear
  a public IP directly.
- "Can X reach Y" starts with: same LAN? public target? or private target
  needing router help?
