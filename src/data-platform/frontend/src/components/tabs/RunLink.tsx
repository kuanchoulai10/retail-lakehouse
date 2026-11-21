import { TextLink } from "@retail-lakehouse/design-system";
import { Link } from "react-router";

function runPath(runId: string): string {
  return `../maintenance?run=${encodeURIComponent(runId)}`;
}

// Shows the whole run id (an mr- id, docs/adr/0011) in monospace; the accessible name carries it too.
export function RunLink({ runId, label, className }: { runId: string; label: string; className?: string }) {
  return (
    <TextLink asChild className={className}>
      <Link to={runPath(runId)} relative="path" aria-label={`Open maintenance run ${runId}`}>
        {label} <span className="font-mono">{runId}</span>
      </Link>
    </TextLink>
  );
}
