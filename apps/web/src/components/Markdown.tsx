import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Lesson/mission body renderer.
 *
 * react-markdown never renders raw HTML embedded in Markdown (it would need
 * rehype-raw, which we deliberately do not install) — so curriculum content
 * cannot inject markup, matching the CSP in infra/docker/Caddyfile. */
export default function Markdown({ children }: { children: string }) {
  return (
    <div className="prose">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}
