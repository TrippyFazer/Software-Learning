import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { postQueued } from "../offline";
import type { AnswerResult, QuizQuestion } from "../types";

/** One quiz question. The answer key lives server-side only: we submit and
 * the backend tells us the outcome + explanation. Answers are not revealed
 * until the learner commits (master plan §8).
 *
 * OFFLINE: the answer is kept on the device and sent later, but it is NOT
 * graded locally. Grading here would require shipping the answer key to the
 * browser — the exact thing Module 0 teaches you not to do, and which the API
 * deliberately prevents by stripping `answer_index` from every quiz payload.
 * So offline you can still sit the quiz; you find out how you did on landing. */
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
  const [queued, setQueued] = useState(false);

  const submit = useMutation({
    mutationFn: (answer: string | number) =>
      postQueued<AnswerResult>(
        "/api/learning/answers",
        { question_id: question.id, answer },
        `Quiz answer: ${question.id}`,
      ),
    onSuccess: (res) => {
      if (res.status === "queued") {
        setQueued(true);
        return;
      }
      setResult(res.data);
      onAnswered?.(res.data.correct);
    },
  });

  const answered = result !== null || queued;

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

      {result && (
        <div className="explanation">
          <strong>{result.correct ? "Correct." : "Not quite."}</strong>{" "}
          {result.explanation}
        </div>
      )}

      {queued && (
        <div className="explanation">
          <strong>Answer recorded.</strong> You are offline, so it will be
          marked when you reconnect — the answer key stays on the server on
          purpose.
        </div>
      )}
    </div>
  );
}
