---
module: docker
lesson: networks-and-ports
title: "Networks and Ports: Who Can Reach What"
difficulty: intermediate
concepts:
  - container-network
  - port-publishing
  - compose-service
prerequisites:
  - docker/images-and-containers
  - networking/ports-and-protocols
quiz: docker/networks-and-ports
flashcards:
  - card-ports
  - card-service-dns
---

## Why this matters

Your server runs two PostgreSQL databases. Neither is reachable from
the internet. Neither is reachable from the *other application*. Both
are reachable by exactly the one API container that owns them. Nobody
configured a firewall rule to achieve that.

Understanding how is the difference between deploying safely and
deploying a database to the public internet by accident — which is a
genuinely common way for small projects to be compromised, because the
default `ports:` line in half the tutorials online does exactly that.

## Mental model

**Beginner mental model:** a Docker network is a private street.
Containers on it know each other by name. Publishing a port drills a
hole from the outside world onto that street.

```
              THE INTERNET
                    │
                    ▼  only published ports
        ┌───────────────────────┐
        │  host: 80, 443 (Caddy)│
        └───────────┬───────────┘
                    │
   ┌────────────────┴────────────────┐   network: proxy
   │  caddy    task-os-api    learning-lab-web
   └────────────────┬────────────────┘
                    │
        ┌───────────┴──────────┐   network: task-os_internal
        │ task-os-api   task-os-postgres
        └──────────────────────┘
                              ▲
                    no published port: unreachable
                    from the host or the internet
```

**Technical reality:** a user-defined bridge network gives every
container an address and — crucially — runs an embedded **DNS
resolver**. Ask for `postgres`, get that container's address on that
network. A container can be on several networks at once, which is how
`task-os-api` reaches both Caddy and its own database while those two
can never see each other.

## Vocabulary

| Term | Plain meaning | Why you care |
|------|---------------|--------------|
| **container network** | A private network with name resolution | How containers find each other |
| **publishing a port** | `ports: "8080:80"` — bind a host port | The only way in from outside |
| **expose** | Documenting a port; no host binding | Often confused with publishing; does nothing on its own |
| **service name** | The DNS name a container answers to | `postgres:5432`, `task-os-api:8000` |

## Deep explanation

**`ports:` is a decision about the public internet.** On a cloud host
with a public IP, `ports: "5432:5432"` on a database means: anyone on
the internet who scans that address finds PostgreSQL. Not "anyone on
your network" — anyone. Bots scan the entire IPv4 space continuously
(Module 3's background radiation, aimed at a different door). This is
why Task OS's database service has a comment where a `ports:` line
would go, saying it is deliberately absent.

**And Docker writes its own firewall rules.** This is the part that
surprises people: publishing a port inserts rules into iptables in a
chain that is evaluated *before* ufw's. A ufw rule denying 5432 will
not save you from a published 5432. On your server the Lightsail
firewall is the authoritative perimeter for exactly this reason, and
ufw is deliberately not enabled — a firewall that appears to be
protecting you and is not is worse than none.

**How containers actually talk.** Look at what the shared Caddy does:

```
reverse_proxy task-os-api:8000
```

`task-os-api` is a container name on the `proxy` network; 8000 is the
port *inside* that container. No host port exists anywhere in that
line. The API is reachable by Caddy and by nothing else. That single
line is the whole architecture of the server: one public door, every
application behind it, addressed by name.

**Networks are the isolation boundary.** `task-os-postgres` is on
`task-os_internal` only. `learning-lab-postgres` is on
`learning-lab_default` only. Neither is on `proxy`. A container can
only resolve names on networks it has joined — so from the Task OS API,
`learning-lab-postgres` does not merely refuse a connection, it does
not *resolve*. There is nothing to attack because there is nothing to
address.

**One caveat worth knowing.** Anything sharing the `proxy` network can
reach anything else on it. `task-os-api` can resolve
`learning-lab-web`. That is inherent to a shared front-end network, and
it is why only web-facing containers join it, and databases never do.

## Brain Core connection

Brain Core will have an API, a database, and probably a worker and a
vector store. Exactly one of those should be on the shared proxy
network. If you find yourself publishing a port to make two of your own
containers talk, you have missed the network — they should be sharing
one and using service names.

## Plex / home-server connection

At home the calculus flips: your Plex server has a *private* address,
so publishing port 32400 exposes it to your LAN, not the world.
Reaching it from outside is then Module 2's journey problem — port
forwarding on the router, or a VPN. The Docker part is the same; what
changed is what "outside" means.

## Interactive example

Run `docker network ls` in the exercise terminal, then bring a stack up
and run it again. A new network appears named `<project>_default`.
Every service in that compose file joined it automatically, and can
reach every other by service name — with no configuration at all.

## Practice

Covered by the compose exercise in the next lesson, where you will fix
a stack that publishes a database to the world.

## Common mistake

> Adding `ports: "5432:5432"` to a database so the application can
> reach it.

It works, which is the problem. The application could already reach it
by service name; the port was added to solve a connection error whose
real cause was a wrong hostname. Now the database is on the public
internet, and it will stay there, because it appears to be working.
If two of your containers cannot talk, the answer is a shared network
and the right name — never a published port.

## Knowledge check

Quiz below.

## Summary

- Containers on a shared user-defined network reach each other **by
  service name**, on the container's own port. No host port involved.
- `ports:` publishes to the host — on a public IP, that is the public
  internet.
- Docker writes iptables rules that bypass ufw. The cloud firewall is
  the real perimeter.
- Networks are the isolation boundary: a name on a network you have not
  joined does not resolve at all.
- Databases belong on a private network with no published port, always.
