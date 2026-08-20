import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import Markdown from "../components/Markdown";
import { QuestionBlock } from "../components/QuizBlock";
import Terminal from "../components/Terminal";
import TerminalUnavailable from "../components/TerminalUnavailable";
import type { ChallengeInfo, ChallengeStatus, TermState } from "../types";

export default function Challenge() {
  const { name } = useParams();
  const slug = name!;
  const qc = useQueryClient();

  const { data: info } = useQuery<ChallengeInfo>({
    queryKey: ["challenge", slug],
    queryFn: () => api.get(`/api/content/challenges/${slug}`),
  });

  const { data: state, isError: termFailed } = useQuery<TermState>({
    queryKey: ["challstate", slug],
    queryFn: () => api.post(`/api/simterm/challenges/${slug}/start`),
    staleTime: Infinity,
  });

  const { data: status, refetch: refetchStatus } = useQuery<ChallengeStatus>({
    queryKey: ["challstatus", slug],
    queryFn: () => api.get(`/api/simterm/challenges/${slug}/status`),
  });

  const input = useMutation({
    mutationFn: (line: string) =>
      api.post<TermState>(`/api/simterm/challenges/${slug}/input`, { line }),
    onSuccess: (next) => {
      qc.setQueryData(["challstate", slug], next);
      void refetchStatus();
    },
  });

  const reset = useMutation({
    mutationFn: () => api.post<TermState>(`/api/simterm/challenges/${slug}/reset`),
    onSuccess: (next) => {
      qc.setQueryData(["challstate", slug], next);
      void refetchStatus();
    },
  });

  // Full do-over: clears completion, question answers, and terminal state,
  // and recomputes mastery from the remaining evidence.
  const fullReset = useMutation({
    mutationFn: () => api.post("/api/learning/reset-item", { item_slug: slug }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["challstate", slug] });
      void qc.invalidateQueries({ queryKey: ["challstatus", slug] });
      void qc.invalidateQueries({ queryKey: ["progress"] });
      void qc.invalidateQueries({ queryKey: ["mastery"] });
      // remount question blocks so answered state clears
      window.location.reload();
    },
  });

  if (termFailed) return <TerminalUnavailable title={info?.title} />;
  if (!info || !state) return <p className="muted">loading…</p>;

  return (
    <>
      <div className="eyebrow">
        <Link to="/curriculum">curriculum</Link> / stage {info.stage} boss
      </div>
      <h1>
        <span className="badge amber">BOSS</span> {info.title}
      </h1>

      {status?.completed && (
        <div className="card" style={{ borderColor: "var(--green)" }}>
          <strong style={{ color: "var(--green)" }}>✓ CHALLENGE COMPLETE</strong>
          {status.success_text && <p className="muted">{status.success_text}</p>}
        </div>
      )}

      <div className="card mt mb">
        <Markdown>{info.briefing}</Markdown>
      </div>

      {info.goal_checklist.length > 0 && (
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
        <span className="muted small">
          Diagnosis: {status?.questions_correct ?? 0}/{status?.questions_total ?? info.questions.length}{" "}
          questions answered correctly
        </span>
        <span>
          <button className="btn ghost" onClick={() => reset.mutate()} disabled={reset.isPending}>
            Reset scenario
          </button>{" "}
          <button
            className="btn ghost"
            title="Erase this challenge's completion, answers, and mastery credit so you can earn it yourself"
            disabled={fullReset.isPending}
            onClick={() => {
              if (
                window.confirm(
                  "Clear this challenge's completion, question answers, and mastery credit? " +
                    "You'll start it from scratch.",
                )
              ) {
                fullReset.mutate();
              }
            }}
          >
            Clear completion
          </button>
        </span>
      </div>

      <h2>Diagnosis questions</h2>
      <p className="muted small">
        Investigate with the terminal first. No hints here — combining what
        you've learned is the challenge.
      </p>
      {info.questions.map((q) => (
        <QuestionBlock key={q.id} question={q} onAnswered={() => void refetchStatus()} />
      ))}
    </>
  );
}
