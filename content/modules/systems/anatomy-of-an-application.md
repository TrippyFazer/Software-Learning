---
module: systems
lesson: anatomy-of-an-application
title: "Anatomy of a Web Application"
difficulty: beginner
concepts:
  - process
  - service
  - application
  - backend
  - frontend
  - database
  - api
prerequisites:
  - systems/what-is-a-server
quiz: systems/anatomy-of-an-application
flashcards:
  - card-process
  - card-service
  - card-backend
  - card-frontend
  - card-database
  - card-api
---

## Why this matters

"Full-stack," "backend," "API," "service" — these words gate-keep almost
every tutorial and every conversation with an AI coding tool. This lesson
dissects one real application — the one you are using right now — so the
words attach to something you can point at. When Claude Code says "I'll add
an endpoint to the backend," you should be able to picture exactly where
that lives.

## Mental model

**Beginner mental model:** a web application is a restaurant.

- The **frontend** is the dining room — everything the customer sees and
  touches.
- The **backend** is the kitchen — where the actual work happens, out of
  sight.
- The **API** is the menu + the order slip: a fixed, agreed format for
  asking the kitchen for things.
- The **database** is the pantry — where everything is stored between
  orders.

**Technical reality:** these are not four machines. They're four *roles*
usually played by two or three programs. In this Lab: your browser runs the
frontend (TypeScript/React code it downloaded); one Python **process** on
the host runs the backend; PostgreSQL — a second process — is the database;
and the API is not a program at all but the *contract* between frontend and
backend (URLs like `/api/auth/login`, and the JSON shapes they accept and
return).

## Vocabulary

| Term | Plain meaning | Why you care |
|------|---------------|--------------|
| **process** | One running program, as the OS sees it | Everything running is one; you'll list them with `ps` |
| **service** | A process meant to run continuously in the background | Your servers are made of these |
| **application** | The whole assembled thing users experience | What you're actually shipping |
| **frontend** | The part that runs on the user's device | Where UX lives |
| **backend** | The part that runs on your server | Where logic, rules, and secrets live |
| **database** | The specialized service that stores data durably | Where state survives restarts |
| **API** | The agreed request/response contract between programs | How parts talk without knowing each other's insides |

## Deep explanation

Start from the OS's point of view. Ubuntu doesn't know what a "web app"
is. It knows **processes**: program X is running, owns some memory, may
touch these files. Run `ps` on the host (Module 1 teaches this) and the
whole grand architecture collapses into a short list of processes —
`caddy`, `uvicorn` (Python), `postgres`.

A **service** is a process with a job description: start at boot, run
forever, restart if you crash. `postgres` is a service. A script you run
once to rename files is a process but not a service.

The **backend/frontend split is a trust boundary, not just a code split.**
The frontend executes on hardware you don't control — the user's browser —
so it can be inspected and modified by anyone. Rules that matter (who is
logged in, what the right quiz answer is) must live in the backend. This
Lab practices what it preaches: quiz answers are never sent to your
browser; you submit an answer and the *backend* grades it.

The **API** is where the two meet. When you pressed "Log in," the frontend
sent `POST /api/auth/login` with a JSON body; the backend answered with JSON
and a cookie. Neither side knows the other's internals — only the contract.
That's what lets you rewrite one side without touching the other, and it's
why Module 11 treats API design as a first-class skill.

The **database** earns its separate box because durability is a distinct,
hard job: surviving power loss mid-write, letting two processes read
consistently, answering "find all attempts since Tuesday" fast. The backend
holds *logic*; the database holds *state*. Restart every process on this
host and your quiz history survives — because it lives in PostgreSQL's
files, not in any process's memory.

An **application** is all of the above, assembled: dining room + kitchen +
menu + pantry, experienced as one restaurant.

## Brain Core connection

Brain Core will have exactly this anatomy: a React (or similar) frontend, a
FastAPI backend enforcing the rules, PostgreSQL holding claims and their
provenance, and an API contract between them. When you review AI-generated
Brain Core code, your first orienting question is now available to you:
*which part of the anatomy is this file?*

## Plex / home-server connection

Plex Media Server is a backend + database bundled into one install; the app
on your TV is a frontend; they speak Plex's API over your LAN. When a
movie won't play, the diagnosis path is the anatomy: is the frontend
fine but the backend down? Is the backend up but its database of media
metadata corrupted?

## Interactive example

On the **About This Server** page, find all four roles in the diagram. Then
open your browser's developer tools (F12 → Network tab) and reload this
page: every row you see is one frontend→backend API request. You are
watching the order slips travel to the kitchen.

## Practice

In your browser's Network tab, find the request that fetched this lesson's
content. What URL did the frontend ask for? Notice you can read the JSON
response — and notice what is *not* in it (no quiz answers).

## Common mistake

> "I'll just have the frontend check the password / grade the quiz / hide
> the admin button — it's easier."

Anything the frontend enforces, the user can un-enforce, because the
frontend runs on *their* machine. Real security and real rules live behind
the API, in the backend. Frontend checks are a courtesy (fast feedback),
never the law. This single misunderstanding is behind a large share of
real-world web vulnerabilities.

## Knowledge check

Quiz below — commit to answers before revealing.

## Summary

- The OS sees only processes; a service is a process meant to run forever.
- Frontend runs on the user's device and cannot be trusted with rules.
- Backend runs on your server and enforces everything that matters.
- The API is the contract between them — URLs and JSON shapes, not code.
- The database is the only place state survives restarts; logic and state
  live in different boxes on purpose.
