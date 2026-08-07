import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api";
import type { Flashcard } from "../types";

/** Flashcard review. Simple honest self-grading against Leitner boxes —
 * the full spaced-repetition scheduler is a future version (ROADMAP). */
export default function Review() {
  const qc = useQueryClient();
  const { data: due } = useQuery<Flashcard[]>({
    queryKey: ["dueCards"],
    queryFn: () => api.get("/api/learning/flashcards/due"),
    staleTime: Infinity,
  });

  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);

  const review = useMutation({
    mutationFn: ({ slug, correct }: { slug: string; correct: boolean }) =>
      api.post("/api/learning/flashcards/review", { card_slug: slug, correct }),
    onSuccess: () => {
      setFlipped(false);
      setIndex((i) => i + 1);
      void qc.invalidateQueries({ queryKey: ["progress"] });
    },
  });

  if (!due) return <p className="muted">loading…</p>;

  const card = due[index];

  return (
    <>
      <h1>Review</h1>
      <p className="subtitle">
        Flashcards due today. Grade yourself honestly — the schedule adapts to
        what you actually remember, and only honest answers make it work.
      </p>

      {!card ? (
        <div className="card">
          <strong>{due.length === 0 ? "Nothing due right now." : "Session complete."}</strong>
          <p className="muted small">
            {due.length === 0
              ? "Cards become due after you complete lessons, and return on a 1/3/7/14-day rhythm."
              : `You reviewed ${due.length} card${due.length > 1 ? "s" : ""}. Come back tomorrow.`}
          </p>
        </div>
      ) : (
        <>
          <p className="muted small mono">
            card {index + 1} / {due.length}
          </p>
          <div
            className="flashcard"
            onClick={() => setFlipped(!flipped)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === " " && setFlipped(!flipped)}
          >
            {flipped ? <span>{card.back}</span> : <span className="front">{card.front}</span>}
          </div>
          {!flipped ? (
            <p className="muted small mt">Recall the definition, then click the card to flip it.</p>
          ) : (
            <div className="spread mt">
              <button
                className="btn ghost"
                disabled={review.isPending}
                onClick={() => review.mutate({ slug: card.slug, correct: false })}
              >
                ✗ Didn't know it
              </button>
              <button
                className="btn green"
                disabled={review.isPending}
                onClick={() => review.mutate({ slug: card.slug, correct: true })}
              >
                ✓ Knew it
              </button>
            </div>
          )}
        </>
      )}
    </>
  );
}
