import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import Markdown from "../components/Markdown";
import Terminal from "../components/Terminal";
import type { Curriculum, ExerciseInfo, TermState } from "../types";

/** /practice                → exercise picker (incl. sandbox)
 *  /practice/:module/:name  → one exercise with terminal */
export default function Practice() {
  const { module, name } = useParams();
  if (module && name) return <ExercisePage slug={`${module}/${name}`} />;
  return <ExercisePicker />;
}

function ExercisePicker() {
  const { data } = useQuery<Curriculum>({
    queryKey: ["curriculum"],
    queryFn: () => api.get("/api/content/curriculum"),
  });

  const exercises =
    data?.modules.flatMap((m) =>
      m.lessons.filter((l) => l.has_exercise).map((l) => ({ lesson: l, moduleTitle: m.title })),
    ) ?? [];

  return (
    <>
      <h1>Practice</h1>
      <p className="subtitle">
        Terminal exercises. Everything here is a simulation — mistakes are free.
      </p>

      <div className="card spread">
        <div>
          <div className="eyebrow">Sandbox</div>
          <strong>Free practice terminal</strong>
          <p className="muted small" style={{ margin: "0.25rem 0 0" }}>
            No mission, no grading. Just try things.
          </p>
        </div>
        <Link to="/practice/practice/sandbox">
          <button className="btn">Open →</button>
        </Link>
      </div>

      <h2>Lesson exercises</h2>
      {exercises.length === 0 && <p className="muted">No exercises yet.</p>}
      {exercises.map(({ lesson, moduleTitle }) => (
        <div className="card spread" key={lesson.slug}>
          <div>
            <div className="eyebrow">{moduleTitle}</div>
            <strong>{lesson.title}</strong>
          </div>
          <Link to={`/lessons/${lesson.slug}`}>
            <button className="btn ghost">Go to lesson →</button>
          </Link>
        </div>
      ))}
    </>
  );
}

function ExercisePage({ slug }: { slug: string }) {
  const qc = useQueryClient();
  const [hints, setHints] = useState<string[]>([]);

  const { data: info } = useQuery<ExerciseInfo>({
    queryKey: ["exercise", slug],
    queryFn: () => api.get(`/api/content/exercises/${slug}`),
  });

  const { data: state } = useQuery<TermState>({
    queryKey: ["termstate", slug],
    queryFn: () => api.post(`/api/simterm/exercises/${slug}/start`),
    staleTime: Infinity,
  });

  const input = useMutation({
    mutationFn: (line: string) =>
      api.post<TermState>(`/api/simterm/exercises/${slug}/input`, { line }),
    onSuccess: (next) => {
      qc.setQueryData(["termstate", slug], next);
      if (next.completed) void qc.invalidateQueries({ queryKey: ["progress"] });
    },
  });

  const reset = useMutation({
    mutationFn: () => api.post<TermState>(`/api/simterm/exercises/${slug}/reset`),
    onSuccess: (next) => qc.setQueryData(["termstate", slug], next),
  });

  async function revealHint() {
    const h = await api.get<{ hint: string }>(
      `/api/content/exercises/${slug}/hints/${hints.length}`,
    );
    setHints((prev) => [...prev, h.hint]);
  }

  if (!info || !state) return <p className="muted">loading…</p>;

  const isSandbox = info.goal_checklist.length === 0;

  return (
    <>
      <div className="eyebrow">
        <Link to="/practice">practice</Link> / {slug}
      </div>
      <h1>{info.title}</h1>
      {state.completed && !isSandbox && (
        <p>
          <span className="badge green">✓ MISSION COMPLETE</span>
        </p>
      )}

      <div className="card mb">
        <Markdown>{info.mission}</Markdown>
      </div>

      {!isSandbox && (
        <ul className="goals">
          {state.goals.map((g) => (
            <li key={g.description} className={g.met ? "met" : ""}>
              <span className="tick">{g.met ? "[✓]" : "[ ]"}</span> {g.description}
            </li>
          ))}
        </ul>
      )}

      <Terminal state={state} busy={input.isPending} onInput={(line) => input.mutate(line)} />

      <div className="spread mt">
        <div>
          {info.hint_count > hints.length && (
            <button className="btn ghost" onClick={revealHint}>
              Reveal hint {hints.length + 1}/{info.hint_count}
            </button>
          )}
        </div>
        <button className="btn ghost" onClick={() => reset.mutate()} disabled={reset.isPending}>
          Reset exercise
        </button>
      </div>
      {hints.map((h, i) => (
        <div className="explanation" key={i}>
          <strong>Hint {i + 1}:</strong> {h}
        </div>
      ))}
    </>
  );
}
