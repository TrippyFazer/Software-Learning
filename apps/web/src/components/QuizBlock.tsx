import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api";
import type { AnswerResult, QuizQuestion } from "../types";

/** One quiz question. The answer key lives server-side only: we submit and
 * the backend tells us the outcome + explanation. Answers are not revealed
 * until the learner commits (master plan §8). */
export function QuestionBlock({
  question,
  onAnswered,
}: {
  question: QuizQuestion;
  onAnswered?: (correct: boolean) => void;
}) {
  const [selected, setSelected] = useState<number | null>(null);
  const [text, setText] = useState("");
  const [result, setResult] = useState<AnswerResult | null>(null);

  const submit = useMutation({
    mutationFn: (answer: string | number) =>
      api.post<AnswerResult>("/api/learning/answers", { question_id: question.id, answer }),
    onSuccess: (res) => {
      setResult(res);
      onAnswered?.(res.correct);
    },
  });

  const answered = result !== null;

  return (
    <div className="card">
      <p style={{ marginTop: 0 }}>{question.prompt}</p>

      {question.type === "multiple_choice" &&
        question.options?.map((opt, i) => {
          let cls = "quiz-option";
          if (!answered && selected === i) cls += " selected";
          if (answered && result) {
            if (i === result.correct_answer) cls += " correct";
            else if (i === selected && !result.correct) cls += " incorrect";
          }
          return (
            <button
              key={i}
              type="button"
              className={cls}
              disabled={answered}
              onClick={() => setSelected(i)}
            >
              {opt}
            </button>
          );
        })}

      {question.type === "text" && (
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={answered}
          placeholder="your answer…"
          onKeyDown={(e) => {
            if (e.key === "Enter" && text.trim() && !answered) submit.mutate(text.trim());
          }}
        />
      )}

      {!answered && (
        <button
          className="btn mt"
          disabled={
            submit.isPending ||
            (question.type === "multiple_choice" ? selected === null : !text.trim())
          }
          onClick={() =>
            submit.mutate(question.type === "multiple_choice" ? selected! : text.trim())
          }
        >
          Check answer
        </button>
      )}

      {answered && result && (
        <div className="explanation">
          <strong>{result.correct ? "Correct." : "Not quite."}</strong>{" "}
          {result.explanation}
        </div>
      )}
    </div>
  );
}
