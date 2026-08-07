import StackDiagram from "../components/StackDiagram";

/** The deployment as course material (master plan §15). Conceptual only —
 * no internal IPs, versions, or secrets appear here. */
export default function AboutServer() {
  return (
    <>
      <h1>About This Server</h1>
      <p className="subtitle">
        The Learning Lab teaches with its own deployment. Everything below is
        the actual path your request took to render this page. Click any layer.
      </p>

      <StackDiagram
        nodes={[
          {
            label: "You (browser)",
            detail:
              "The client. It downloaded the frontend (a TypeScript/React bundle) and runs it locally. Every action you take becomes an HTTPS request to /api/*.",
          },
          {
            label: "learn.example.com (DNS)",
            detail:
              "The Domain Name System translates the memorable name into the server's IP address. Your browser did this lookup before it could connect (Module 2).",
          },
          {
            label: "Lightsail static IP",
            detail:
              "A fixed public IP address rented from AWS and attached to the instance, so DNS always has a stable target even if the instance is rebuilt.",
          },
          {
            label: "Ubuntu Linux (the host)",
            detail:
              "The operating system on the rented machine. It runs the processes, enforces permissions, and owns the firewall — only ports 22 (SSH), 80, and 443 are open.",
          },
          {
            label: "Port 443 → Caddy",
            detail:
              "Caddy is the reverse proxy: it terminates HTTPS (it obtained the TLS certificate automatically), sets security headers, serves the frontend files, and forwards /api/* inward. It is the only internet-facing process.",
          },
          {
            label: "Docker network",
            detail:
              "The containers share a private virtual network. Caddy can reach the API; the outside world cannot reach anything but Caddy. The database is never exposed.",
          },
          {
            label: "Learning Lab API (FastAPI)",
            detail:
              "The backend — a Python process. It checks your session cookie, loads lessons from version-controlled content, grades your answers, and runs the simulated terminal (a pure simulation: your commands never touch this host).",
          },
          {
            label: "PostgreSQL",
            detail:
              "The database, in its own container with a persistent volume. It stores learner state only: attempts, mastery, progress. The curriculum itself lives in git, not here.",
          },
        ]}
      />

      <h2>Things worth noticing</h2>
      <div className="card">
        <ul style={{ margin: 0, paddingLeft: "1.2rem" }}>
          <li>
            <strong>Three open ports, no more.</strong> SSH for administration, 80
            for HTTPS setup/redirect, 443 for the app. Everything else — including
            the database — is unreachable from the internet.
          </li>
          <li>
            <strong>Your login is a cookie, not a token in JavaScript.</strong>{" "}
            The session lives server-side; the browser holds an opaque HttpOnly
            cookie that scripts can't read (Module 21 territory).
          </li>
          <li>
            <strong>The terminal you practice in is a simulation.</strong> A real
            shell exposed to a browser would be a serious vulnerability. You'll
            learn exactly why in Modules 3 and 22 — using this very design as the
            case study.
          </li>
          <li>
            <strong>Containers are disposable; your progress isn't.</strong> The
            database writes to a persistent volume, so containers can be rebuilt
            freely — a distinction Module 8 (Docker) makes hands-on.
          </li>
        </ul>
      </div>
    </>
  );
}
