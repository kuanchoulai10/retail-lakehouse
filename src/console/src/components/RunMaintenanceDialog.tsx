import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { apiSend } from "../api/client";
import { errorMessage } from "../format";

export const ALL_OPERATIONS = [
  "rewrite_data_files",
  "rewrite_manifests",
  "expire_snapshots",
  "remove_orphan_files",
];

interface Props {
  tableUuid: string;
  initialOperations?: string[];
  onClose: () => void;
}

export function RunMaintenanceDialog({
  tableUuid,
  initialOperations = ALL_OPERATIONS,
  onClose,
}: Props) {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<string[]>(initialOperations);
  const run = useMutation({
    mutationFn: () =>
      apiSend("POST", `/v1/tables/${tableUuid}/maintenance`, {
        operations: ALL_OPERATIONS.filter((op) => selected.includes(op)),
      }),
    onSuccess: async () => {
      await Promise.all(
        ["runs", "health"].map((key) => queryClient.invalidateQueries({ queryKey: [key, tableUuid] })),
      );
      onClose();
    },
  });

  function toggle(operation: string) {
    setSelected((current) =>
      current.includes(operation) ? current.filter((o) => o !== operation) : [...current, operation],
    );
  }

  return (
    <div role="dialog" aria-label="Run maintenance" className="dialog">
      <h2>Run maintenance</h2>
      <p className="muted">Runs on the whole table, ignoring thresholds</p>
      {ALL_OPERATIONS.map((operation) => (
        <label key={operation} className="check">
          <input
            type="checkbox"
            checked={selected.includes(operation)}
            onChange={() => toggle(operation)}
          />
          {operation}
        </label>
      ))}
      {run.isError && (
        <p role="alert" className="error">
          Could not start maintenance: {errorMessage(run.error)}
        </p>
      )}
      <div className="actions">
        <button type="button" onClick={onClose}>
          Cancel
        </button>
        <button
          type="button"
          className="primary"
          disabled={selected.length === 0 || run.isPending}
          onClick={() => run.mutate()}
        >
          Run
        </button>
      </div>
    </div>
  );
}
