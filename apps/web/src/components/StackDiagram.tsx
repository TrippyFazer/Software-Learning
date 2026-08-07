import { useState } from "react";

export interface StackNode {
  label: string;
  detail: string;
}

/** The reusable architecture diagram: a vertical chain of clickable nodes.
 * Deliberately not a graphics engine — readable beats fancy
 * (master plan §14). */
export default function StackDiagram({ nodes }: { nodes: StackNode[] }) {
  const [open, setOpen] = useState<number | null>(null);

  return (
    <div className="stack-diagram">
      {nodes.map((node, i) => (
        <div key={node.label} style={{ display: "contents" }}>
          {i > 0 && <div className="stack-arrow">↓</div>}
          <button
            type="button"
            className={`stack-node ${open === i ? "open" : ""}`}
            onClick={() => setOpen(open === i ? null : i)}
            title="Click to explain"
          >
            {node.label}
          </button>
          {open === i && <div className="stack-detail">{node.detail}</div>}
        </div>
      ))}
    </div>
  );
}
