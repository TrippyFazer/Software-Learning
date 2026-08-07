import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api";
import type { MasteryEntry, Progress } from "../types";

/** Concept-level mastery, with the full breakdown visible — mastery must be
 * explainable, never a black box (docs/ARCHITECTURE.md). */
export default function ProgressPage() {
  const { data: p } = useQuery<Progress>({
    queryKey: ["progress"],
    queryFn: () => api.get("/api/learning/progress"),
  });
  const { data: mastery } = useQuery<MasteryEntry[]>({
    queryKey: ["mastery"],
    queryFn: () => api.get("/api/learning/mastery"),
  });
  const [open, setOpen] = useState<string | null>(null);

  if (!p || !mastery) return <p className="muted">loading…</p>;

  return (
    <>
      <h1>Progress</h1>
      <p className="subtitle">
        Mastery is computed per concept from evidence — click any concept to
        see exactly why it has the score it has.
      </p>

      <div className="statrow">
        <div className="stat">
          <div className="value">{p.lessons_completed}</div>
          <div className="label">lessons completed</div>
        </div>
        <div className="stat">
          <div className="value">{p.concepts_mastered}</div>
          <div className="label">concepts ≥ 80%</div>
        </div>
        <div className="stat">
          <div className="value">{p.study_minutes_recent}</div>
          <div className="label">recent study minutes</div>
        </div>
      </div>

      <h2>Concept mastery</h2>
      {mastery.length === 0 && (
        <p className="muted">No evidence yet — complete a lesson to begin.</p>
      )}
      {mastery.map((m) => (
        <div className="card" key={m.concept} style={{ marginTop: "0.6rem" }}>
          <button
            onClick={() => setOpen(open === m.concept ? null : m.concept)}
            style={{ all: "unset", cursor: "pointer", display: "block", width: "100%" }}
          >
            <div className="spread">
              <span>
                <strong>{m.term}</strong>{" "}
                <span className="faint mono small">{m.concept}</span>
              </span>
              <span className="mono">{Math.round(m.score * 100)}%</span>
            </div>
            <div className={`bar mt ${m.score >= 0.8 ? "green" : ""}`}>
              <div style={{ width: `${m.score * 100}%` }} />
            </div>
          </button>
          {open === m.concept && (
            <div className="mt small">
              {Object.entries(m.breakdown).map(([kind, ev]) => (
                <div className="listrow" key={kind}>
                  <span className="mono">{kind}</span>
                  <span className="muted">
                    {"achieved" in ev && ev.achieved !== undefined
                      ? ev.achieved
                        ? "✓ achieved"
                        : "not yet"
                      : ev.total !== undefined
                        ? `${ev.correct}/${ev.total} correct`
                        : ""}
                    {"  "}
                    <span className="faint">
                      (weight {ev.weight}
                      {ev.earned !== undefined ? `, earned ${ev.earned}` : ""})
                    </span>
                    {ev.note && <span className="faint"> — {ev.note}</span>}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </>
  );
}
