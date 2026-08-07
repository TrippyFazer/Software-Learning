import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import Markdown from "../components/Markdown";
import { QuestionBlock } from "../components/QuizBlock";
import type { Lesson, LessonProgressMap, Quiz } from "../types";

export default function LessonPage() {
  const { module, lesson } = useParams();
  const slug = `${module}/${lesson}`;
  const qc = useQueryClient();
  const [quizOpen, setQuizOpen] = useState(false);

  const { data, error } = useQuery<Lesson>({
    queryKey: ["lesson", slug],
    queryFn: () => api.get(`/api/content/lessons/${slug}`),
  });

  const { data: progress } = useQuery<LessonProgressMap>({
    queryKey: ["lessonProgress"],
    queryFn: () => api.get("/api/learning/lessons/progress"),
  });

  const quiz = useQuery<Quiz>({
    queryKey: ["quiz", data?.quiz],
    queryFn: () => api.get(`/api/content/quizzes/${data!.quiz}`),
    enabled: !!data?.quiz && quizOpen,
  });

  // Mark the lesson started on first view.
  useEffect(() => {
    if (data) void api.post(`/api/learning/lessons/${slug}/start`);
  }, [data, slug]);

  const complete = useMutation({
    mutationFn: () => api.post(`/api/learning/lessons/${slug}/complete`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["lessonProgress"] });
      void qc.invalidateQueries({ queryKey: ["progress"] });
    },
  });

  if (error) return <p className="error-text">Lesson not found.</p>;
  if (!data) return <p className="muted">loading…</p>;

  const done = progress?.[slug]?.completed;

  return (
    <>
      <div className="eyebrow">
        {data.module} / {data.difficulty}
      </div>
      <h1>{data.title}</h1>
      <p className="subtitle">
        Concepts:{" "}
        {data.concepts.map((c) => (
          <span key={c} className="badge" style={{ marginRight: 4 }}>
            {c}
          </span>
        ))}
      </p>

      <Markdown>{data.body}</Markdown>

      {data.exercise && (
        <div className="card mt spread">
          <div>
            <div className="eyebrow">Practice</div>
            <strong>Terminal exercise for this lesson</strong>
          </div>
          <Link to={`/practice/${data.exercise}`}>
            <button className="btn">Open terminal →</button>
          </Link>
        </div>
      )}

      {data.quiz && (
        <>
          <h2>Knowledge check</h2>
          {!quizOpen ? (
            <button className="btn" onClick={() => setQuizOpen(true)}>
              Start quiz
            </button>
          ) : quiz.data ? (
            quiz.data.questions.map((q) => <QuestionBlock key={q.id} question={q} />)
          ) : (
            <p className="muted">loading quiz…</p>
          )}
        </>
      )}

      <div className="card mt spread">
        <span className="muted small">
          {done
            ? "Lesson completed — its concepts are marked as introduced."
            : "Finished reading and practicing? Mark it complete to record the concepts as introduced."}
        </span>
        <button
          className={`btn ${done ? "green" : ""}`}
          disabled={complete.isPending || done}
          onClick={() => complete.mutate()}
        >
          {done ? "✓ Completed" : "Mark complete"}
        </button>
      </div>
    </>
  );
}
