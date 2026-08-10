import { useEffect, useRef, useState } from "react";
import type { TermState } from "../types";

/** The simulated terminal UI. All command handling happens server-side in a
 * pure simulation — this component renders transcript + input line, and
 * reproduces the shell's *feel*: focus never leaves the prompt, ↑/↓ walk
 * command history, Ctrl+C abandons the current line, Ctrl+L clears the
 * screen. */
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
  // History navigation: null = not navigating; otherwise index into history.
  const [histIndex, setHistIndex] = useState<number | null>(null);
  const draftRef = useRef("");           // what was typed before pressing ↑
  const [clearedAt, setClearedAt] = useState(0); // Ctrl+L: hide entries before this index
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Server-side `clear` command marker: show only entries after the last one.
  let entries = state.transcript;
  const lastClear = entries.map((e) => e.output[0]).lastIndexOf("\x00clear");
  const cutoff = Math.max(lastClear + 1, clearedAt);
  entries = entries.slice(cutoff);

  // History = every command in the transcript (persisted server-side, so it
  // survives leaving and coming back — like a real ~/.bash_history).
  const history = state.transcript.map((e) => e.input);

  useEffect(() => {
    const el = scrollRef.current;
    // feature-detect: jsdom (tests) has no scrollTo
    if (el && typeof el.scrollTo === "function") {
      el.scrollTo({ top: el.scrollHeight });
    }
  }, [state.transcript.length, clearedAt]);

  // The input stays enabled (disabling a focused element throws focus out of
  // the terminal — the "kicked back to the page" bug). Keep focus pinned
  // after each command completes.
  useEffect(() => {
    if (!busy) inputRef.current?.focus();
  }, [busy, state.transcript.length]);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = line.trim();
    if (!trimmed || busy) return;
    onInput(trimmed);
    setLine("");
    setHistIndex(null);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (history.length === 0) return;
      if (histIndex === null) {
        draftRef.current = line;           // save the unfinished line
        setHistIndex(history.length - 1);
        setLine(history[history.length - 1]);
      } else if (histIndex > 0) {
        setHistIndex(histIndex - 1);
        setLine(history[histIndex - 1]);
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (histIndex === null) return;
      if (histIndex < history.length - 1) {
        setHistIndex(histIndex + 1);
        setLine(history[histIndex + 1]);
      } else {
        setHistIndex(null);
        setLine(draftRef.current);         // walked past the end: restore draft
      }
    } else if (e.key === "c" && e.ctrlKey) {
      e.preventDefault();                  // like the shell: abandon the line
      setLine("");
      setHistIndex(null);
    } else if (e.key === "l" && e.ctrlKey) {
      e.preventDefault();                  // like the shell: clear the screen
      setClearedAt(state.transcript.length);
    } else if (histIndex !== null && e.key.length === 1) {
      // typing while browsing history: adopt the recalled line as the draft
      setHistIndex(null);
    }
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
          <div key={cutoff + i}>
            <div className="line-input">
              <span className="ps1">
                {ps1(i === 0 ? entries[0].cwd_after : entries[i - 1]?.cwd_after ?? state.cwd)}
              </span>{" "}
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
          onKeyDown={onKeyDown}
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
