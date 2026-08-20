import { useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { api } from "../api";
import { cacheMe } from "../App";
import { purgeOfflineData, useOnline, useOutboxCount, useOutboxFlush } from "../offline";
import type { Me } from "../types";

const links = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/curriculum", label: "Curriculum" },
  { to: "/practice", label: "Practice" },
  { to: "/vocabulary", label: "Vocabulary" },
  { to: "/review", label: "Review" },
  { to: "/progress", label: "Progress" },
  { to: "/offline", label: "Offline & install" },
  { to: "/about-server", label: "About This Server" },
];

export default function Layout({ me, children }: { me: Me; children: ReactNode }) {
  const qc = useQueryClient();
  const online = useOnline();
  const queued = useOutboxCount();

  // Mounted exactly once, here rather than per page: two concurrent flushes
  // could send the same queued write twice.
  useOutboxFlush();

  async function logout() {
    // Best-effort: offline, the server-side session cannot be revoked now, so
    // clear everything locally and let the cookie expire. Silently doing
    // nothing would leave someone believing they had logged out.
    try {
      await api.post("/api/auth/logout");
    } catch {
      /* offline — proceed with the local teardown regardless */
    }
    cacheMe(null);
    await purgeOfflineData();
    qc.clear();
    // Full reload: guarantees no in-memory state survives the session.
    window.location.href = "/";
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <span className="prompt">learner@lab</span>:~$ <span className="faint">▮</span>
        </div>
        <nav>
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} className={({ isActive }) => (isActive ? "active" : "")}>
              {l.label}
              {l.to === "/offline" && queued > 0 && <span className="nav-badge">{queued}</span>}
            </NavLink>
          ))}
        </nav>
        <div className="spacer" />
        <div className="userbox">
          <div>{me.display_name}</div>
          <button onClick={logout}>log out</button>
        </div>
      </aside>
      <main className="main">
        {/* Says what is true and what to do about it — not just "offline". */}
        {!online && (
          <div className="offline-bar" role="status">
            <strong>Offline.</strong> Downloaded lessons, vocabulary and
            flashcards work. Terminal exercises and progress scores need the
            server. Anything you complete is saved here and sent when you
            reconnect.
          </div>
        )}
        {online && queued > 0 && (
          <div className="sync-bar" role="status">
            Syncing {queued} item{queued > 1 ? "s" : ""} recorded offline…
          </div>
        )}
        {children}
      </main>
    </div>
  );
}
