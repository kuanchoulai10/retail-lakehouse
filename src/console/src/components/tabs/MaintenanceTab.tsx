import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { apiGet } from "../../api/client";
import type { JsonObject, TableMaintenanceRunApiResponse } from "../../api/types";
import { errorMessage, formatDuration, formatTimestamp } from "../../format";

function OperationDetail({ operation }: { operation: JsonObject }) {
  const attempts = Number(operation.attempts ?? 0);
  const metrics = Object.entries((operation.metrics as Record<string, number> | undefined) ?? {});
  const error = operation.error as string | null | undefined;
  return (
    <li>
      <strong>{String(operation.operation)}</strong>{" "}
      <span className={`badge badge-${String(operation.status)}`}>
        {String(operation.status).toUpperCase()}
      </span>{" "}
      <span className="muted">{`${attempts} ${attempts === 1 ? "attempt" : "attempts"}`}</span>
      {metrics.length > 0 && (
        <ul>
          {metrics.map(([name, value]) => (
            <li key={name}>{`${name}: ${value}`}</li>
          ))}
        </ul>
      )}
      {error && <p className="error">{error}</p>}
    </li>
  );
}

function RunRow({ run }: { run: TableMaintenanceRunApiResponse }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <tr className="clickable" onClick={() => setOpen(!open)}>
        <td>{run.trigger}</td>
        <td>
          <span className={`badge badge-${run.status}`}>{run.status.toUpperCase()}</span>
        </td>
        <td>{formatTimestamp(run.created_at)}</td>
        <td>{formatDuration(run.created_at, run.finished_at)}</td>
      </tr>
      {open && (
        <tr>
          <td colSpan={4}>
            <p>
              Execution: <code>{run.execution_ref}</code>
            </p>
            <ul>
              {run.operations.map((op) => (
                <OperationDetail key={String(op.operation)} operation={op} />
              ))}
            </ul>
          </td>
        </tr>
      )}
    </>
  );
}

export function MaintenanceTab({ tableUuid }: { tableUuid: string }) {
  const runs = useQuery({
    queryKey: ["runs", tableUuid],
    queryFn: () =>
      apiGet<TableMaintenanceRunApiResponse[]>(`/v1/tables/${tableUuid}/table-maintenance-runs`),
  });

  if (runs.isPending) return <p>Loading runs…</p>;
  if (runs.isError) {
    return (
      <p role="alert" className="error">
        Could not load maintenance runs: {errorMessage(runs.error)}
      </p>
    );
  }
  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Trigger</th>
          <th>Status</th>
          <th>Started</th>
          <th>Duration</th>
        </tr>
      </thead>
      <tbody>
        {runs.data.map((run) => (
          <RunRow key={run.run_id} run={run} />
        ))}
        {runs.data.length === 0 && (
          <tr>
            <td colSpan={4} className="empty">
              No maintenance runs yet.
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}
