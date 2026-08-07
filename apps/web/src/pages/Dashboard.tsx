import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { Progress } from "../types";

export default function Dashboard() {
  const { data: p } = useQuery<Progress>({
    queryKey: ["progress"],
    queryFn: () => api.get("/api/learning/progress"),
  });

  if (!p) return <p className="muted">loading…</p>;

  const currentModule = p.modules.find(
    (m) => m.implemented && m.lessons_completed < m.lessons_total,
  );
  const stage = currentModule?.stage ?? 1;

  return (
    <>
      <div className="eyebrow">Stage {stage} — Computing Foundations</div>
      <h1>Dashboard</h1>
      <p className="subtitle">
        {currentModule
          ? `Current module: ${currentModule.title}`
          : "All implemented modules complete."}
      </p>

      <div className="statrow">
        <div className="stat">
          <div className="value">{p.lessons_completed}</div>
          <div className="label">lessons completed</div>
        </div>
        <div className="stat">
          <div className="value">{p.concepts_mastered}</div>
          <div className="label">concepts mastered (≥80%)</div>
        </div>
        <div className="stat">
          <div className="value">{p.concepts_tracked}</div>
          <div className="label">concepts in training</div>
        </div>
        <div className="stat">
          <div className="value">{p.due_flashcards}</div>
          <div className="label">flashcards due</div>
        </div>
      </div>

      {p.next_lesson && (
        <div className="card spread">
          <div>
            <div className="eyebrow">Next recommended lesson</div>
            <strong className="mono">{p.next_lesson}</strong>
          </div>
          <Link to={`/lessons/${p.next_lesson}`}>
            <button className="btn">Continue →</button>
          </Link>
        </div>
      )}

      <h2>Modules</h2>
      <div className="card">
        {p.modules.map((m) => (
          <div className="listrow" key={m.id}>
            <span>
              <span className="faint mono small">M{m.number}</span>{" "}
              {m.implemented ? (
                <Link to="/curriculum">{m.title}</Link>
              ) : (
                <span className="muted">{m.title}</span>
              )}
            </span>
            <span className="small muted mono">
              {m.implemented ? `${m.lessons_completed}/${m.lessons_total}` : "planned"}
            </span>
          </div>
        ))}
      </div>

      <div className="cardgrid mt">
        <div className="card">
          <div className="eyebrow">Recently learned</div>
          {p.recently_learned.length === 0 && <p className="muted small">Nothing yet — start a lesson.</p>}
          {p.recently_learned.map((c) => (
            <div className="listrow" key={c.concept}>
              <span className="mono small">{c.concept}</span>
              <span className="badge accent">{Math.round(c.score * 100)}%</span>
            </div>
          ))}
        </div>
        <div className="card">
          <div className="eyebrow">Needs review</div>
          {p.needs_review.length === 0 && <p className="muted small">Nothing weak right now.</p>}
          {p.needs_review.map((c) => (
            <div className="listrow" key={c.concept}>
              <span className="mono small">{c.concept}</span>
              <span className="badge amber">{Math.round(c.score * 100)}%</span>
            </div>
          ))}
          {p.due_flashcards > 0 && (
            <Link to="/review" className="small">
              Review {p.due_flashcards} due flashcard{p.due_flashcards > 1 ? "s" : ""} →
            </Link>
          )}
        </div>
      </div>
    </>
  );
}
