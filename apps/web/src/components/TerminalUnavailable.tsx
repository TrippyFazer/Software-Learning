import { Link } from "react-router-dom";
import { useOnline } from "../offline";

/**
 * Shown where a terminal would be when the simulator cannot be reached.
 *
 * The terminal is the one part of the Lab that genuinely cannot work offline,
 * and it is worth being precise about WHY rather than showing a spinner: every
 * command is tokenised and applied to a virtual filesystem by the server
 * (`apps/api/app/modules/simterm/`). Nothing runs in the browser — which is
 * exactly the property that makes the terminal safe, and exactly the property
 * that makes it need a network.
 */
export default function TerminalUnavailable({ title }: { title?: string }) {
  const online = useOnline();
  return (
    <>
      {title && <h1>{title}</h1>}
      <div className="card">
        <strong>{online ? "The simulator is unreachable." : "Terminal exercises need a network."}</strong>
        <p className="muted small">
          Every command you type is graded by the simulator on the server, and
          nothing is executed in your browser. That is what makes it impossible
          to damage anything — and why there is nothing to run offline.
        </p>
        <p className="muted small">
          Reading, vocabulary and flashcards all work without a network. See{" "}
          <Link to="/offline">Offline &amp; install</Link>.
        </p>
      </div>
    </>
  );
}
