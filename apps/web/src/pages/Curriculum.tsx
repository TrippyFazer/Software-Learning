import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { Curriculum as CurriculumT, LessonProgressMap } from "../types";

const STAGE_NAMES: Record<number, string> = {
  1: "Computing Foundations",
  2: "Infrastructure",
  3: "Software Engineering",
  4: "Brain Core Concepts",
  5: "Production Systems",
  6: "Engineering Mastery",
};

export default function Curriculum() {
  const { data } = useQuery<CurriculumT>({
    queryKey: ["curriculum"],
    queryFn: () => api.get("/api/content/curriculum"),
  });
  const { data: progress } = useQuery<LessonProgressMap>({
    queryKey: ["lessonProgress"],
    queryFn: () => api.get("/api/learning/lessons/progress"),
  });

  if (!data) return <p className="muted">loading…</p>;

  const stages = [...new Set(data.modules.map((m) => m.stage))].sort();

  return (
    <>
      <h1>Curriculum</h1>
      <p className="subtitle">
        The full learning path. Unimplemented modules are shown so you can see
        where this is going — they unlock in future versions.
      </p>

      {stages.map((stage) => (
        <section key={stage}>
          <h2>
            Stage {stage} — {STAGE_NAMES[stage] ?? ""}
          </h2>
          {data.modules
            .filter((m) => m.stage === stage)
            .map((m) => (
              <div className="card" key={m.id}>
                <div className="spread">
                  <strong>
                    <span className="faint mono">M{m.number}</span> {m.title}
                  </strong>
                  {!m.implemented && <span className="badge">planned</span>}
                </div>
                <p className="muted small" style={{ margin: "0.35rem 0 0.6rem" }}>
                  {m.description}
                </p>
                {m.lessons.map((l) => {
                  const done = progress?.[l.slug]?.completed;
                  return (
                    <div className="listrow" key={l.slug}>
                      <span>
                        <Link to={`/lessons/${l.slug}`}>{l.title}</Link>{" "}
                        {l.has_exercise && <span className="badge accent">terminal</span>}{" "}
                        {l.has_quiz && <span className="badge">quiz</span>}
                      </span>
                      <span className={`small mono ${done ? "" : "faint"}`} style={done ? { color: "var(--green)" } : {}}>
                        {done ? "✓ done" : "○"}
                      </span>
                    </div>
                  );
                })}
              </div>
            ))}
          {data.challenges
            .filter((c) => c.stage === stage)
            .map((c) => (
              <div className="card" key={c.id} style={{ borderColor: "var(--amber)" }}>
                <div className="spread">
                  <strong>
                    <span className="badge amber">BOSS</span> {c.title}
                  </strong>
                  <Link to={`/challenges/${c.id}`}>
                    <button className="btn ghost">Enter →</button>
                  </Link>
                </div>
              </div>
            ))}
        </section>
      ))}
    </>
  );
}
