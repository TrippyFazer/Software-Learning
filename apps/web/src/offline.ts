/* =============================================================================
   Offline support
   =============================================================================
   Three separate problems, deliberately kept separate:

     1. Can the app LOAD with no network?          -> service worker (public/sw.js)
     2. Can it SHOW the curriculum with no network? -> prefetch + SW content cache
     3. What happens to what you DO with no network? -> the outbox, below

   (3) is the one that is usually got wrong. The tempting answer is to let the
   service worker retry failed POSTs in the background. That produces writes
   the learner cannot see, cannot cancel, and cannot explain — landing hours
   later, in an order nobody chose. So the queue lives here instead: in
   IndexedDB, listed in the UI, with a visible count and a way to discard it.

   WHAT IS NOT QUEUED, AND WHY

   - Quiz grading. The backend holds the answer key and the frontend never
     receives it (see apps/api/.../content/router.py `_strip_answers`) — which
     is not an oversight, it is a LESSON in this very curriculum
     ("Why must quiz grading happen in the backend?"). So offline you can still
     answer; you get the result when you reconnect. Making it instant would
     mean shipping the answer key onto the device and contradicting the thing
     the app teaches.
   - Anything destructive. reset-item / reset-lesson / reset-all are never
     queued. A deletion that fires silently three hours later, after you have
     forgotten you asked, is indefensible.
   - Login and logout. An auth transition that happens later is a bug.
   ============================================================================= */

import { useEffect, useState } from "react";

import { ApiError } from "./api";

const DB_NAME = "learning-lab-offline";
const DB_VERSION = 1;
const STORE = "outbox";

export interface QueuedWrite {
  id?: number;
  path: string;
  body: unknown;
  /** Shown to the learner, so the queue is legible rather than a row count. */
  label: string;
  queued_at: string;
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: "id", autoIncrement: true });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function tx<T>(mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return openDb().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const t = db.transaction(STORE, mode);
        const req = fn(t.objectStore(STORE));
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
        t.oncomplete = () => db.close();
      }),
  );
}

export const outbox = {
  all: () => tx<QueuedWrite[]>("readonly", (s) => s.getAll() as IDBRequest<QueuedWrite[]>),
  add: (item: QueuedWrite) => tx("readwrite", (s) => s.add(item)),
  remove: (id: number) => tx("readwrite", (s) => s.delete(id)),
  clear: () => tx("readwrite", (s) => s.clear()),
};

/** Anything the outbox is allowed to replay. An allowlist, not a denylist:
 *  a new destructive endpoint must be opted IN, never accidentally included. */
const QUEUEABLE = [
  /^\/api\/learning\/lessons\/[^/]+\/[^/]+\/(start|complete)$/,
  /^\/api\/learning\/flashcards\/review$/,
  /^\/api\/learning\/answers$/,
];

export function isQueueable(path: string): boolean {
  return QUEUEABLE.some((re) => re.test(path));
}

export type PostResult<T> = { status: "sent"; data: T } | { status: "queued" };

/**
 * POST, and if the NETWORK is the thing that failed, queue it instead of
 * losing it.
 *
 * The distinction matters: an ApiError means the server answered and said no
 * (404, 400, 401). Replaying that later would just fail again, so it is
 * rethrown. Only a genuine transport failure — fetch rejecting — is queued.
 * `navigator.onLine` is not consulted, because it lies: it reports true on a
 * captive portal and on an aircraft wifi that sells you internet you have not
 * bought yet.
 */
export async function postQueued<T>(
  path: string,
  body: unknown,
  label: string,
): Promise<PostResult<T>> {
  try {
    const res = await fetch(path, {
      method: "POST",
      credentials: "same-origin",
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const parsed = await res.json();
        if (typeof parsed.detail === "string") detail = parsed.detail;
      } catch {
        /* non-JSON error body */
      }
      throw new ApiError(res.status, detail);
    }
    return { status: "sent", data: (await res.json()) as T };
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (!isQueueable(path)) throw err;
    await outbox.add({ path, body, label, queued_at: new Date().toISOString() });
    window.dispatchEvent(new CustomEvent("outbox:changed"));
    return { status: "queued" };
  }
}

/**
 * Send everything waiting, oldest first, deleting each item the moment its
 * POST succeeds.
 *
 * Deleting per-item rather than at the end bounds the damage from a crash
 * mid-flush to a single replayed write. That matters because the API has no
 * idempotency keys: replaying `flashcards/review` twice would advance a card's
 * Leitner box twice. One duplicated card review is survivable; replaying a
 * whole session is not.
 *
 * A write the server REJECTS is dropped, not retried forever — a permanently
 * poisoned queue would block every good write behind it.
 */
export async function flushOutbox(): Promise<{ sent: number; failed: number }> {
  const items = (await outbox.all()).sort((a, b) => a.queued_at.localeCompare(b.queued_at));
  let sent = 0;
  let failed = 0;
  for (const item of items) {
    try {
      const res = await fetch(item.path, {
        method: "POST",
        credentials: "same-origin",
        headers: item.body === undefined ? undefined : { "Content-Type": "application/json" },
        body: item.body === undefined ? undefined : JSON.stringify(item.body),
      });
      if (res.ok) {
        await outbox.remove(item.id!);
        sent += 1;
      } else if (res.status >= 400 && res.status < 500) {
        // The server will never accept this. Keeping it would block the queue.
        await outbox.remove(item.id!);
        failed += 1;
      } else {
        break; // 5xx: the server is unwell. Stop and try again later.
      }
    } catch {
      break; // still offline
    }
  }
  if (sent || failed) window.dispatchEvent(new CustomEvent("outbox:changed"));
  return { sent, failed };
}

/* -------------------------------------------------------------------------- */
/*  Making the curriculum available offline                                    */
/* -------------------------------------------------------------------------- */

export interface DownloadProgress {
  done: number;
  total: number;
  current: string;
}

/**
 * Walk the whole curriculum and request every content URL once, so the
 * service worker's content cache holds it.
 *
 * This is EXPLICIT rather than automatic. Silently downloading everything the
 * first time someone opens the app would be a surprise on a metered phone
 * connection, and "it just happened to be cached" is not something you can
 * rely on the night before a flight. A button you press, with a count you can
 * read, is something you can trust.
 */
export async function downloadForOffline(
  onProgress: (p: DownloadProgress) => void,
): Promise<{ ok: number; failed: number }> {
  const curriculum = await fetch("/api/content/curriculum", {
    credentials: "same-origin",
  }).then((r) => r.json());

  const urls: { url: string; label: string }[] = [
    { url: "/api/content/curriculum", label: "curriculum" },
    { url: "/api/content/vocabulary", label: "vocabulary" },
    { url: "/api/content/flashcards", label: "flashcards" },
  ];

  for (const mod of curriculum.modules ?? []) {
    for (const lesson of mod.lessons ?? []) {
      urls.push({ url: `/api/content/lessons/${lesson.slug}`, label: lesson.title });
    }
  }
  for (const ch of curriculum.challenges ?? []) {
    urls.push({ url: `/api/content/challenges/${ch.id}`, label: ch.title });
  }

  let ok = 0;
  let failed = 0;
  let done = 0;

  // Sequential on purpose: 40-odd small requests, and hammering the API with
  // a parallel burst on a 2-vCPU shared host is rude for no gain.
  for (const { url, label } of urls) {
    onProgress({ done, total: urls.length, current: label });
    try {
      const res = await fetch(url, { credentials: "same-origin" });
      if (res.ok) {
        ok += 1;
        // Lessons name their own quiz — fetch it in the same pass, otherwise
        // the quiz is missing exactly when you sit down to take it.
        const payload = await res.clone().json();
        if (payload?.quiz) {
          await fetch(`/api/content/quizzes/${payload.quiz}`, { credentials: "same-origin" });
        }
      } else {
        failed += 1;
      }
    } catch {
      failed += 1;
    }
    done += 1;
  }
  onProgress({ done, total: urls.length, current: "" });
  return { ok, failed };
}

/* -------------------------------------------------------------------------- */
/*  Service worker registration                                                */
/* -------------------------------------------------------------------------- */

export function registerServiceWorker(): void {
  if (!("serviceWorker" in navigator)) return;
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      /* An unregistered worker means no offline support, not a broken app. */
    });
  });
}

/** Wipe every cache and the queue. Used on logout: a shared device must not
 *  keep one learner's cached pages readable by the next person. */
export async function purgeOfflineData(): Promise<void> {
  try {
    await outbox.clear();
  } catch {
    /* database may not exist yet */
  }
  navigator.serviceWorker?.controller?.postMessage({ type: "PURGE" });
  if ("caches" in window) {
    const keys = await caches.keys();
    await Promise.all(keys.map((k) => caches.delete(k)));
  }
}

/* -------------------------------------------------------------------------- */
/*  React bindings                                                             */
/* -------------------------------------------------------------------------- */


/**
 * Whether the browser believes it has a network.
 *
 * Used ONLY for what the interface says, never to decide whether to attempt a
 * request. `navigator.onLine` means "a network interface is up", not "the
 * internet is reachable" — it is true on a captive portal and on aircraft wifi
 * you have not paid for. Every real decision in this module is made from
 * whether a fetch actually succeeded.
 */
export function useOnline(): boolean {
  const [online, setOnline] = useState(navigator.onLine);
  useEffect(() => {
    const up = () => setOnline(true);
    const down = () => setOnline(false);
    window.addEventListener("online", up);
    window.addEventListener("offline", down);
    return () => {
      window.removeEventListener("online", up);
      window.removeEventListener("offline", down);
    };
  }, []);
  return online;
}

/** How many writes are waiting to be sent. */
export function useOutboxCount(): number {
  const [count, setCount] = useState(0);
  useEffect(() => {
    let alive = true;
    const refresh = () =>
      outbox
        .all()
        .then((items) => alive && setCount(items.length))
        .catch(() => undefined);
    refresh();
    window.addEventListener("outbox:changed", refresh);
    window.addEventListener("online", refresh);
    return () => {
      alive = false;
      window.removeEventListener("outbox:changed", refresh);
      window.removeEventListener("online", refresh);
    };
  }, []);
  return count;
}

/**
 * Try to drain the queue whenever a network appears, and once at startup.
 *
 * Mounted once, in Layout — not per page, or a queue would be flushed several
 * times concurrently and the same write could be sent twice.
 */
export function useOutboxFlush(): void {
  useEffect(() => {
    let running = false;
    const run = () => {
      if (running) return;
      running = true;
      void flushOutbox().finally(() => {
        running = false;
      });
    };
    run();
    window.addEventListener("online", run);
    return () => window.removeEventListener("online", run);
  }, []);
}

/* -------------------------------------------------------------------------- */
/*  Install prompt                                                             */
/* -------------------------------------------------------------------------- */

/**
 * Chromium fires `beforeinstallprompt` once, early — usually before React has
 * mounted — and it can only be used in response to a user gesture. So it is
 * captured at startup and held here until the learner presses a button.
 *
 * Safari and Firefox never fire it; installing there is a manual menu action,
 * so the UI explains that path instead of pretending a button will appear.
 */
interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

let deferredPrompt: InstallPromptEvent | null = null;

export function captureInstallPrompt(): void {
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault(); // stop the browser's own mini-infobar
    deferredPrompt = e as InstallPromptEvent;
    window.dispatchEvent(new CustomEvent("install:available"));
  });
  window.addEventListener("appinstalled", () => {
    deferredPrompt = null;
    window.dispatchEvent(new CustomEvent("install:available"));
  });
}

export function canInstall(): boolean {
  return deferredPrompt !== null;
}

export async function promptInstall(): Promise<"accepted" | "dismissed" | "unavailable"> {
  if (!deferredPrompt) return "unavailable";
  await deferredPrompt.prompt();
  const { outcome } = await deferredPrompt.userChoice;
  deferredPrompt = null;
  window.dispatchEvent(new CustomEvent("install:available"));
  return outcome;
}

/** True when running as an installed app rather than in a browser tab. */
export function isInstalled(): boolean {
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    // iOS Safari predates the standard and uses a non-standard property.
    (navigator as unknown as { standalone?: boolean }).standalone === true
  );
}
