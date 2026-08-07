import { useEffect, useRef, useState } from "react";
import type { TermState } from "../types";

/** The simulated terminal UI. All command handling happens server-side in a
 * pure simulation — this component just renders transcript + input line. */
export default function Terminal({
  state,
  onInput,
  busy,
}: {
  state: TermState;
  onInput: (line: string) => void;
  busy: boolean;
}) {
  const [line, setLine] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Handle the \x00clear marker: show only entries after the last clear.
  let entries = state.transcript;
  const lastClear = entries.map((e) => e.output[0]).lastIndexOf("\x00clear");
  if (lastClear >= 0) entries = entries.slice(lastClear + 1);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [state.transcript.length]);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = line.trim();
    if (!trimmed || busy) return;
    onInput(trimmed);
    setLine("");
  }

  const ps1 = (cwd: string) => {
    const short = cwd === "/home/learner" ? "~" : cwd.replace(/^\/home\/learner/, "~");
    return `learner@lab:${short}$`;
  };

  return (
    <div className="terminal" onClick={() => inputRef.current?.focus()}>
      <div className="titlebar">
        <span>simulated shell — safe sandbox</span>
        <span>{state.cwd}</span>
      </div>
      <div className="scrollback" ref={scrollRef}>
        {entries.map((entry, i) => (
          <div key={i}>
            <div className="line-input">
              <span className="ps1">{ps1(i === 0 ? entries[0].cwd_after : entries[i - 1]?.cwd_after ?? state.cwd)}</span>{" "}
              {entry.input}
            </div>
            {entry.output
              .filter((l) => l !== "\x00clear")
              .map((l, j) => (
                <div key={j} className="line-output">
                  {l}
                </div>
              ))}
          </div>
        ))}
      </div>
      <form onSubmit={submit}>
        <span className="ps1">{ps1(state.cwd)}</span>
        <input
          ref={inputRef}
          value={line}
          onChange={(e) => setLine(e.target.value)}
          disabled={busy}
          autoFocus
          autoComplete="off"
          autoCapitalize="off"
          spellCheck={false}
          aria-label="terminal input"
        />
      </form>
    </div>
  );
}
