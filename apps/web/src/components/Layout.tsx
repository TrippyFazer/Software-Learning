import { useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { api } from "../api";
import type { Me } from "../types";

const links = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/curriculum", label: "Curriculum" },
  { to: "/practice", label: "Practice" },
  { to: "/vocabulary", label: "Vocabulary" },
  { to: "/review", label: "Review" },
  { to: "/progress", label: "Progress" },
  { to: "/about-server", label: "About This Server" },
];

export default function Layout({ me, children }: { me: Me; children: ReactNode }) {
  const qc = useQueryClient();

  async function logout() {
    await api.post("/api/auth/logout");
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
            </NavLink>
          ))}
        </nav>
        <div className="spacer" />
        <div className="userbox">
          <div>{me.display_name}</div>
          <button onClick={logout}>log out</button>
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
