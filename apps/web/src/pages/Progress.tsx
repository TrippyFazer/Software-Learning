import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api";
import type { MasteryEntry, Progress } from "../types";

interface CompletedItems {
  lessons: { slug: string; title: string }[];
  exercises: { slug: string; title: string }[];
  challenges: { slug: string; title: string }[];
}

/** Concept-level mastery with the full breakdown visible — mastery must be
 * explainable, never a black box (docs/ARCHITECTURE.md) — plus the reset
 * controls for everything marked complete. */
export default function ProgressPage() {
  const qc = useQueryClient();
  const { data: p } = useQuery<Progress>({
    queryKey: ["progress"],
    queryFn: () => api.get("/api/learning/progress"),
  });
  const { data: mastery } = useQuery<MasteryEntry[]>({
    queryKey: ["mastery"],
    queryFn: () => api.get("/api/learning/mastery"),
  });
  const { data: completed } = useQuery<CompletedItems>({
    queryKey: ["completedItems"],
    queryFn: () => api.get("/api/learning/completed-items"),
  });
  const [open, setOpen] = useState<string | null>(null);

  function refreshAll() {
    void qc.invalidateQueries({ queryKey: ["progress"] });
    void qc.invalidateQueries({ queryKey: ["mastery"] });
    void qc.invalidateQueries({ queryKey: ["completedItems"] });
    void qc.invalidateQueries({ queryKey: ["lessonProgress"] });
    // terminal states may have been wiped too
    void qc.invalidateQueries({ queryKey: ["termstate"] });
    void qc.invalidateQueries({ queryKey: ["challstate"] });
    void qc.invalidateQueries({ queryKey: ["challstatus"] });
  }

  const resetItem = useMutation({
    mutationFn: (slug: string) => api.post("/api/learning/reset-item", { item_slug: slug }),
    onSuccess: refreshAll,
  });
  const resetLesson = useMutation({
    mutationFn: (slug: string) => api.post("/api/learning/reset-lesson", { lesson_slug: slug }),
    onSuccess: refreshAll,
  });
  const resetAll = useMutation({
    mutationFn: () => api.post("/api/learning/reset-all", { confirm: "reset everything" }),
    onSuccess: refreshAll,
  });

  function confirmReset(kind: string, title: string, fn: () => void) {
    if (
      window.confirm(
        `Reset ${kind} "${title}"? Its completion and the mastery credit it earned ` +
          "will be cleared so you can do it again from scratch.",
      )
    ) {
      fn();
    }
  }

  if (!p || !mastery) return <p className="muted">loading…</p>;

  const anyCompleted =
    completed &&
    completed.lessons.length + completed.exercises.length + completed.challenges.length > 0;

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

      <h2>Manage progress</h2>
      <p className="muted small">
        Reset anything marked complete — its completion and the mastery credit
        it earned are cleared, and your scores are recomputed from the
        evidence that remains. Useful when someone else used your session, or
        when you want to re-earn something honestly.
      </p>

      {!anyCompleted && (
        <div className="card">
          <span className="muted small">Nothing is marked complete yet.</span>
        </div>
      )}

      {completed && completed.challenges.length > 0 && (
        <div className="card">
          <div className="eyebrow">Completed challenges</div>
          {completed.challenges.map((c) => (
            <div className="listrow" key={c.slug}>
              <span>
                <span className="badge amber">BOSS</span> {c.title}
              </span>
              <button
                className="btn ghost"
                disabled={resetItem.isPending}
                onClick={() => confirmReset("challenge", c.title, () => resetItem.mutate(c.slug))}
              >
                Reset
              </button>
            </div>
          ))}
        </div>
      )}

      {completed && completed.exercises.length > 0 && (
        <div className="card">
          <div className="eyebrow">Completed exercises</div>
          {completed.exercises.map((e) => (
            <div className="listrow" key={e.slug}>
              <span>{e.title}</span>
              <button
                className="btn ghost"
                disabled={resetItem.isPending}
                onClick={() => confirmReset("exercise", e.title, () => resetItem.mutate(e.slug))}
              >
                Reset
              </button>
            </div>
          ))}
        </div>
      )}

      {completed && completed.lessons.length > 0 && (
        <div className="card">
          <div className="eyebrow">Completed lessons</div>
          {completed.lessons.map((l) => (
            <div className="listrow" key={l.slug}>
              <span>
                {l.title} <span className="faint mono small">{l.slug}</span>
              </span>
              <button
                className="btn ghost"
                disabled={resetLesson.isPending}
                onClick={() => confirmReset("lesson", l.title, () => resetLesson.mutate(l.slug))}
              >
                Reset
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="card mt" style={{ borderColor: "var(--red)" }}>
        <div className="eyebrow" style={{ color: "var(--red)" }}>
          Danger zone
        </div>
        <div className="spread">
          <span className="muted small">
            Erase ALL progress: every attempt, mastery score, lesson
            completion, terminal state, and flashcard history. There is no
            undo (short of restoring a database backup).
          </span>
          <button
            className="btn ghost"
            style={{ borderColor: "var(--red)", color: "var(--red)" }}
            disabled={resetAll.isPending}
            onClick={() => {
              const phrase = window.prompt(
                'This erases everything. Type "reset everything" to confirm:',
              );
              if (phrase === "reset everything") resetAll.mutate();
              else if (phrase !== null) window.alert("Phrase didn't match — nothing was reset.");
            }}
          >
            Reset all progress
          </button>
        </div>
      </div>
    </>
  );
}
