# Curriculum

The complete learning sequence. Only **Modules 0–3** (plus the Stage 1 boss
challenge) ship with content in v0.1; everything else is planned structure.

Every module teaches toward two real systems the learner is building:
**Brain Core** (personal/organizational intelligence platform) and a
**Plex/home-server** environment — plus the Lightsail deployment of this very
application.

## Teaching loop

```
LEARN → VISUALIZE → PRACTICE → MAKE A MISTAKE → UNDERSTAND WHY
      → TRY AGAIN → APPLY → REVIEW LATER
```

## Lesson format

Every lesson supports these sections (see `content/modules/*/`):

1. **Why this matters** — why the concept exists at all
2. **Mental model** — intuition before terminology; beginner mental model
   explicitly distinguished from technical reality
3. **Vocabulary** — term / definition / why I care (first use highlighted)
4. **Deep explanation** — the real technical content
5. **Brain Core connection** — where this appears in Brain Core
6. **Plex / home-server connection** — where this appears there
7. **Interactive example** — something to manipulate or inspect
8. **Practice** — required doing (usually simulated terminal)
9. **Common mistake** — a realistic beginner failure, and why it happens
10. **Knowledge check** — answers not immediately revealed
11. **Summary** — ~5 takeaways
12. **Flashcards** — term → definition pairs

## Stages and modules

### Stage 1 — Computing Foundations ✅ v0.1 content

| # | Module | Core concepts |
|---|--------|---------------|
| 0 | Computing Systems Mental Model | server, client, host, hardware, OS, process, service, application, backend, frontend, database, API |
| 1 | Linux Fundamentals | filesystem, paths, pwd/ls/cd/mkdir/touch/cat, users, permissions, processes, services, logs |
| 2 | Networking Fundamentals | LAN, WAN, IP, public/private IP, router, DNS, domain, port, TCP, HTTP, HTTPS, firewall, reverse proxy, bandwidth, latency — incl. "What happens when I type learn.example.com?" |
| 3 | SSH and Remote Administration | SSH, port 22, remote shell, public/private keys, authorized_keys, known_hosts, password vs key auth |

**Boss: SERVER ROOKIE** — a Linux server where a web application has stopped
working. Given filesystem state, processes, disk usage, service state, and
logs, diagnose the problem. Requires combining Stage 1 concepts; the answer
is never named in the prompt.

### Stage 2 — Infrastructure

| # | Module | Focus |
|---|--------|-------|
| 4 | Storage Fundamentals | disks, partitions, filesystems, mounts, RAID concepts |
| 5 | Server Hardware | CPU, RAM, storage tiers, NICs, what specs actually mean |
| 6 | Plex Fundamentals | media libraries, clients, streaming vs transcoding |
| 7 | Virtualization and Proxmox | VMs, hypervisors, containers vs VMs |
| 8 | Docker | images, containers, volumes, networks, Compose — taught partly using *this app's own* Compose file |

*(Note: the master plan lists Storage in Stage 1 and hardware onward in
Stage 2; storage content is scheduled with Stage 2 delivery but numbered
Module 4 either way.)*

### Stage 3 — Software Engineering

| # | Module |
|---|--------|
| 9 | Git and GitHub |
| 10 | Software Architecture |
| 11 | Web Applications and APIs |
| 12 | PostgreSQL and Relational Databases |

### Stage 4 — Brain Core Concepts

| # | Module |
|---|--------|
| 13 | Brain Core Domain Model |
| 14 | Provenance and Trust (claim → measurement → assay → sample → protocol → operator) |
| 15 | AI Fundamentals |
| 16 | Embeddings and Vector Search |
| 17 | RAG |
| 18 | Chunking and Document Ingestion |
| 19 | Retrieval Quality |

### Stage 5 — Production Systems

| # | Module |
|---|--------|
| 20 | Events, Jobs, and Automation |
| 21 | Authentication and Authorization (taught partly from this app's own auth) |
| 22 | Security |
| 23 | Cloud Computing |
| 24 | Home Server vs Cloud |
| 25 | Backups and Disaster Recovery |
| 26 | Observability |
| 27 | Local AI and GPU Compute |

### Stage 6 — Engineering Mastery

| # | Module |
|---|--------|
| 28 | System Design |
| 29 | AI-Assisted Software Development |
| 30 | Capstone Architecture |

Each stage ends with a cumulative **boss challenge** that requires combining
several concepts without being told which ones.

## Project ladder (cumulative, spanning stages)

| Project | Deliverable understanding |
|---------|---------------------------|
| A — Linux Server Sandbox | files, directories, permissions, processes, services, logs |
| B — Deploy a Website | DNS, ports, HTTPS, reverse proxy, Docker |
| C — Plex Architecture | media, storage, network, transcoding, Quick Sync |
| D — PostgreSQL Application | structured data creation and querying |
| E — FastAPI Application | requests, endpoints, backend logic |
| F — Mini Retrieval System | chunks, embeddings, search |
| G — Brain Core Architecture | explain the real Brain Core system |
| H — Home Server Design | design Plex/storage/home-lab infrastructure |

## Mastery and review

- Mastery is tracked per **concept** with evidence: introduced, quiz
  accuracy, command exercise, applied exercise, (future) delayed retention
  check. Scores are explainable — the learner can always see *why* a
  concept is at 72%.
- Attempt history is preserved append-only so a real spaced-repetition
  scheduler can be added in a later version without data loss (v0.1 ships a
  simple "needs review" surface, not a full SRS).

## Content authoring

Lessons are Markdown + YAML frontmatter under `content/`. To add a lesson:
copy an existing one, keep the frontmatter schema (validated at load time),
give concepts stable slugs, and add quiz/flashcard/exercise files referencing
those slugs. No application code changes required.
