# ADR-0007: Offline reading as a progressive web app

Status: Accepted · Date: 2026-08-20

## Context

The learner asked to study on a plane. The Lab is a SPA talking to a FastAPI
backend, so with no network it did not degrade — it failed completely, and in
the most misleading way available: the boot sequence calls `/api/auth/me`,
that request failed, every failure was treated as "not signed in", and the app
showed a login form that also could not reach the server.

Most of what the Lab teaches is reading. The curriculum is version-controlled
Markdown and YAML, identical for every learner and changing only on deploy —
it is about as cacheable as data gets. Making it unavailable in a tunnel was
an accident of architecture, not a requirement.

## Decision

Ship offline support in three separate layers, each with a different owner.

**1. Service worker (`apps/web/public/sw.js`) — hand-written, no Workbox.**
The build tool is not allowed to generate the one file that permanently sits
between the app and the network. Navigations are network-first so a deploy is
picked up as soon as the device is online; only `/assets/*` is cache-first,
and only because Vite puts a content hash in those filenames. Every cache name
carries a `VERSION` and `activate` deletes everything else.

**2. Explicit download, not ambient caching.**
`/offline` has a button that walks the curriculum and fetches every lesson,
quiz, vocabulary entry and flashcard. Automatic background downloading would
be a surprise on a metered phone connection, and "it happened to be cached" is
not something you can rely on the night before a flight.

**3. An outbox the learner can see (`apps/web/src/offline.ts`).**
Writes made offline go to IndexedDB and are replayed on reconnect. They are
NOT replayed by the service worker: a worker silently re-sending POSTs hours
later produces state nobody authorised and nobody can cancel. The queue is
listed in the UI with a count, a "sync now" and a "discard".

Three things are deliberately excluded from the queue: destructive resets
(a deletion that fires three hours after you forgot you asked is
indefensible), login/logout (an auth transition that happens later is a bug),
and anything the server must decide.

## Consequences

**Quizzes can be taken offline but not marked offline.** `_strip_answers` in
`modules/content/router.py` removes `answer_index` from every quiz payload, so
the browser never holds the answer key. That is not an oversight — it is the
subject of a question in Module 0 ("Why must quiz grading happen in the
backend?"). Grading offline would mean shipping the key onto the device and
contradicting the thing the app teaches. So the answer is queued and marked on
reconnect, and the UI says exactly that.

If instant offline feedback is ever judged more valuable than the consistency,
the change is small and must be deliberate: ship the key only into the offline
cache, on explicit opt-in, and say so on the button.

**Terminal exercises do not work offline, and cannot.** Every command is
tokenised and applied to the virtual filesystem in `modules/simterm/` — on the
server. Porting the interpreter to TypeScript would create a second
implementation of the one component whose safety is guaranteed by tests
(`test_simterm_safety.py`), and two implementations drift. The pages say so
instead of spinning on "loading…".

**A non-credential identity now lives in `localStorage`** (`ill.me`: email and
display name). This does not weaken hard rule 5 — the session is still an
opaque server-side token in an HttpOnly cookie, and this value grants nothing.
It only answers "whose name goes in the sidebar, and do I render the app or
the login form?" A 401 clears it; logout clears it and purges every cache.

**Mastery and progress scores are never served stale.** Read-only projections
whose staleness is harmless (`flashcards/due`, `lessons/progress`) fall back to
cache; scores do not. A number that looks authoritative and is quietly hours
out of date is worse than an honest blank.

**The Lab is installable.** A manifest and icons mean it gets an application
icon and its own window rather than living as a bookmark — which also makes
iOS keep the cache, since on iOS "Add to Home Screen" is the only route to
reliable offline storage.
