import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api } from "../api";
import type { VocabTerm } from "../types";

export default function Vocabulary() {
  const { data } = useQuery<VocabTerm[]>({
    queryKey: ["vocabulary"],
    queryFn: () => api.get("/api/content/vocabulary"),
  });
  const [filter, setFilter] = useState("");

  const terms = useMemo(() => {
    if (!data) return [];
    const q = filter.trim().toLowerCase();
    if (!q) return data;
    return data.filter(
      (t) =>
        t.term.toLowerCase().includes(q) ||
        t.mental_model.toLowerCase().includes(q) ||
        t.technical.toLowerCase().includes(q),
    );
  }, [data, filter]);

  if (!data) return <p className="muted">loading…</p>;

  return (
    <>
      <h1>Vocabulary</h1>
      <p className="subtitle">
        Every term, two ways: the beginner mental model and the technical
        reality. Intuition first, precision second — you need both.
      </p>

      <div className="field" style={{ maxWidth: 340 }}>
        <input
          type="text"
          placeholder="filter terms…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          aria-label="filter vocabulary"
        />
      </div>

      {terms.map((t) => (
        <div className="vocab-term" key={t.slug}>
          <h3>
            {t.term} <span className="badge">{t.module}</span>
          </h3>
          <div className="row">
            <span className="k">Mental model</span>
            {t.mental_model}
          </div>
          <div className="row">
            <span className="k">Technical reality</span>
            {t.technical}
          </div>
          <div className="row">
            <span className="k">Why it matters</span>
            {t.why_it_matters}
          </div>
          {t.related.length > 0 && (
            <div className="row">
              <span className="k">Related</span>
              {t.related.map((r) => (
                <span key={r} className="badge" style={{ marginRight: 4 }}>
                  {r}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
      {terms.length === 0 && <p className="muted">No matching terms.</p>}
    </>
  );
}
