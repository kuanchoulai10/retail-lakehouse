import { useState } from "react";
import type { TableHealthApiResponse, TableHealthOperationApiResponse } from "../api/types";
import { formatTimestamp } from "../format";
import { RunMaintenanceDialog } from "./RunMaintenanceDialog";

function measurement(line: TableHealthOperationApiResponse): string {
  const { measured, threshold } = line;
  if (measured === null) return line.verdict === "due" ? "due" : "not due";
  const suffix = threshold === null ? "" : `, threshold ${threshold}`;
  switch (line.operation) {
    case "rewrite_data_files": {
      const partitions =
        line.qualifying_partitions === null ? "" : ` in ${line.qualifying_partitions} ${line.qualifying_partitions === 1 ? "partition" : "partitions"}`;
      return `${measured} reducible files${partitions}${suffix}`;
    }
    case "rewrite_manifests":
      return `${measured} small manifests${suffix}`;
    case "expire_snapshots":
      return `${measured} snapshots past retention${suffix}`;
    default:
      return `${measured}${suffix}`;
  }
}

function lineText(line: TableHealthOperationApiResponse, scheduled: boolean): string {
  switch (line.verdict) {
    case "disabled":
      return "disabled";
    case "cooldown":
      return line.next_eligible_at === null
        ? "in cooldown"
        : `in cooldown until ${formatTimestamp(line.next_eligible_at)}`;
    case "due":
      return scheduled ? measurement(line) : `${measurement(line)} (would be due when resumed)`;
    case "not_due":
      return line.measured === null ? measurement(line) : `${measurement(line)} (not due)`;
    default:
      return `${line.verdict}: ${measurement(line)}`;
  }
}

interface Props {
  tableUuid: string;
  health: TableHealthApiResponse;
}

export function HealthPanel({ tableUuid, health }: Props) {
  const [runOperation, setRunOperation] = useState<string | null>(null);
  return (
    <section className="panel" aria-label="Health">
      <h2>Health</h2>
      {!health.scheduled && (
        <p role="status" className="notice">
          {`The scheduler skips this table: ${health.not_scheduled_reason ?? "unknown"}`}
        </p>
      )}
      <ul className="health-lines">
        {health.operations.map((line) => (
          <li key={line.operation}>
            <strong>{line.operation}</strong>
            <span className={`health-${line.verdict}`}>{lineText(line, health.scheduled)}</span>
            {health.scheduled && line.verdict === "due" && (
              <button type="button" onClick={() => setRunOperation(line.operation)}>
                Run now
              </button>
            )}
          </li>
        ))}
      </ul>
      <dl className="facts">
        <dt>Delete files</dt>
        <dd>{`${health.position_delete_files} position, ${health.equality_delete_files} equality`}</dd>
      </dl>
      {runOperation !== null && (
        <RunMaintenanceDialog
          tableUuid={tableUuid}
          initialOperations={[runOperation]}
          onClose={() => setRunOperation(null)}
        />
      )}
    </section>
  );
}
