import { useEffect, useState } from "react";
import {
  canInstall,
  downloadForOffline,
  flushOutbox,
  isInstalled,
  outbox,
  promptInstall,
  useOnline,
  type DownloadProgress,
  type QueuedWrite,
} from "../offline";

/** What actually works with no network, stated plainly.
 *
 *  Being specific here is the whole point. "Works offline" is a claim people
 *  discover to be false at 35,000 feet, which is the worst possible moment.
 *  Anything that cannot work is listed as loudly as the things that can. */
const CAPABILITIES: { what: string; works: boolean; why: string }[] = [
  { what: "Reading lessons", works: true, why: "Downloaded and cached on your device." },
  { what: "Vocabulary", works: true, why: "Downloaded with everything else." },
  { what: "Flashcard review", works: true, why: "Cards carry their own answers; grading is yours." },
  { what: "Marking a lesson complete", works: true, why: "Queued and sent when you reconnect." },
  {
    what: "Answering quiz questions",
    works: true,
    why: "Answers are queued — but you see whether you were right only once you reconnect. The answer key lives on the server, deliberately; that is the lesson in Module 0.",
  },
  {
    what: "Terminal exercises",
    works: false,
    why: "Every command is graded by the simulator on the server. Nothing runs in your browser, so there is nothing to run offline.",
  },
  {
    what: "Progress and mastery scores",
    works: false,
    why: "Calculated from your full history in the database.",
  },
];

export default function OfflinePage() {
  const online = useOnline();
  const [installable, setInstallable] = useState(canInstall());
  const [progress, setProgress] = useState<DownloadProgress | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [queue, setQueue] = useState<QueuedWrite[]>([]);
  const [usage, setUsage] = useState<string | null>(null);

  const refreshQueue = () => outbox.all().then(setQueue).catch(() => undefined);

  useEffect(() => {
    const onAvail = () => setInstallable(canInstall());
    window.addEventListener("install:available", onAvail);
    window.addEventListener("outbox:changed", refreshQueue);
    void refreshQueue();
    if (navigator.storage?.estimate) {
      void navigator.storage.estimate().then((e) => {
        if (e.usage) setUsage(`${(e.usage / 1024 / 1024).toFixed(1)} MB stored on this device`);
      });
    }
    return () => {
      window.removeEventListener("install:available", onAvail);
      window.removeEventListener("outbox:changed", refreshQueue);
    };
  }, []);

  async function download() {
    setResult(null);
    setProgress({ done: 0, total: 1, current: "starting" });
    try {
      const r = await downloadForOffline(setProgress);
      setResult(
        r.failed === 0
          ? `Ready. ${r.ok} items are on this device.`
          : `${r.ok} downloaded, ${r.failed} failed — try again while online.`,
      );
      if (navigator.storage?.estimate) {
        const e = await navigator.storage.estimate();
        if (e.usage) setUsage(`${(e.usage / 1024 / 1024).toFixed(1)} MB stored on this device`);
      }
    } catch {
      setResult("Download failed — are you online?");
    } finally {
      setProgress(null);
    }
  }

  return (
    <>
      <h1>Offline &amp; install</h1>
      <p className="subtitle">
        Download the curriculum before you lose signal, and install the Lab so
        it opens like an app instead of a bookmark.
      </p>

      {/* ---------------------------------------------------------- install */}
      <h2>Install</h2>
      {isInstalled() ? (
        <div className="card">
          <strong>Installed.</strong>
          <p className="muted small" style={{ margin: "0.25rem 0 0" }}>
            You are running the installed app. It has its own icon and window,
            and it opens without a browser.
          </p>
        </div>
      ) : installable ? (
        <div className="card spread">
          <div>
            <strong>Install the Learning Lab</strong>
            <p className="muted small" style={{ margin: "0.25rem 0 0" }}>
              Adds it to your applications or home screen.
            </p>
          </div>
          <button className="btn" onClick={() => void promptInstall()}>
            Install
          </button>
        </div>
      ) : (
        <div className="card">
          <strong>Install from your browser's menu</strong>
          <p className="muted small">
            Your browser does not offer an install button to the page, so it is
            a menu action:
          </p>
          <ul className="muted small">
            <li>
              <b>iPhone / iPad (Safari):</b> Share → <i>Add to Home Screen</i>.
              This is the only way on iOS, and it is required for offline use.
            </li>
            <li>
              <b>Chrome / Edge desktop:</b> the install icon at the right-hand
              end of the address bar, or ⋮ → <i>Cast, save and share</i> →{" "}
              <i>Install page as app</i>.
            </li>
            <li>
              <b>Firefox:</b> no installed-app mode on desktop; offline still
              works in a normal tab.
            </li>
          </ul>
        </div>
      )}

      {/* --------------------------------------------------------- download */}
      <h2>Download for offline</h2>
      <div className="card">
        <p className="muted small" style={{ marginTop: 0 }}>
          Fetches every lesson, quiz, vocabulary entry and flashcard and keeps
          them on this device. Do it on wifi, before you travel. It is a few
          megabytes of text.
        </p>
        {progress && (
          <p className="mono small">
            {progress.done}/{progress.total} — {progress.current}
          </p>
        )}
        {result && <p className="small">{result}</p>}
        {usage && <p className="muted small mono">{usage}</p>}
        <button className="btn" disabled={!online || progress !== null} onClick={() => void download()}>
          {progress ? "Downloading…" : "Download everything"}
        </button>
        {!online && (
          <p className="muted small">
            You are offline — reconnect to download. Anything you downloaded
            earlier is still available.
          </p>
        )}
      </div>

      {/* ------------------------------------------------------- what works */}
      <h2>What works with no network</h2>
      <div className="card">
        {CAPABILITIES.map((c) => (
          <div key={c.what} className="cap-row">
            <span className={c.works ? "cap-yes" : "cap-no"}>{c.works ? "✓" : "✗"}</span>
            <div>
              <strong>{c.what}</strong>
              <div className="muted small">{c.why}</div>
            </div>
          </div>
        ))}
      </div>

      {/* ------------------------------------------------------------ queue */}
      <h2>Waiting to sync</h2>
      <div className="card">
        {queue.length === 0 ? (
          <p className="muted small" style={{ margin: 0 }}>
            Nothing waiting. Everything you have done is on the server.
          </p>
        ) : (
          <>
            <p className="small" style={{ marginTop: 0 }}>
              {queue.length} thing{queue.length > 1 ? "s" : ""} recorded on this
              device and not yet sent. They go automatically the moment you are
              back online.
            </p>
            <ul className="muted small mono">
              {queue.map((q) => (
                <li key={q.id}>
                  {new Date(q.queued_at).toLocaleString()} — {q.label}
                </li>
              ))}
            </ul>
            <div className="spread">
              <button
                className="btn ghost"
                onClick={() => {
                  if (
                    window.confirm(
                      `Discard ${queue.length} unsent item(s)? This work will be lost.`,
                    )
                  ) {
                    void outbox.clear().then(refreshQueue);
                  }
                }}
              >
                Discard
              </button>
              <button
                className="btn"
                disabled={!online}
                onClick={() => void flushOutbox().then(refreshQueue)}
              >
                Sync now
              </button>
            </div>
          </>
        )}
      </div>
    </>
  );
}
