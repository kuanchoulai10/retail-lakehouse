import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { apiSend } from "../api/client";
import type { TableApiResponse, TableMetadataApiResponse } from "../api/types";
import { errorMessage, formatBytes, formatCount, formatRelativeTime } from "../format";
import { RunMaintenanceDialog } from "./RunMaintenanceDialog";

interface Props {
  table: TableApiResponse;
  metadata: TableMetadataApiResponse | undefined;
}

function averageFileSize(metadata: TableMetadataApiResponse): string {
  const { total_files_size_bytes: bytes, total_data_files: files } = metadata;
  if (bytes === null || files === null || files === 0) return "avg —";
  return `avg ${formatBytes(bytes / files)} / file`;
}

export function TableHeader({ table, metadata }: Props) {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const paused = table.status.toLowerCase() === "paused";
  const toggle = useMutation({
    mutationFn: () => apiSend("POST", `/v1/tables/${table.uuid}/${paused ? "resume" : "pause"}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["table", table.uuid] }),
  });

  return (
    <header className="table-header">
      <div className="table-title">
        <h1>{`${table.catalog}.${table.namespace}.${table.table}`}</h1>
        <span className={`badge badge-${table.status.toLowerCase()}`}>
          {table.status.toUpperCase()}
        </span>
        <span className="muted">Preset: {table.source_preset_id ?? "—"}</span>
        <span className="muted">Rule: {table.matched_rule_id ?? "—"}</span>
        <span className="spacer" />
        <button type="button" onClick={() => setDialogOpen(true)}>
          Run maintenance
        </button>
        <button type="button" disabled={toggle.isPending} onClick={() => toggle.mutate()}>
          {paused ? "Resume" : "Pause"}
        </button>
      </div>
      {toggle.isError && (
        <p role="alert" className="error">
          Could not change the table: {errorMessage(toggle.error)}
        </p>
      )}
      {metadata && (
        <div className="summary">
          <span>{formatCount(metadata.total_records)} rows</span>
          <span>{formatCount(metadata.total_data_files)} data files</span>
          <span>
            {metadata.total_files_size_bytes === null
              ? "—"
              : formatBytes(metadata.total_files_size_bytes)}
          </span>
          <span>{averageFileSize(metadata)}</span>
          <span>{formatCount(metadata.snapshot_count)} snapshots</span>
          <span>last commit {formatRelativeTime(metadata.last_committed_at)}</span>
        </div>
      )}
      {dialogOpen && (
        <RunMaintenanceDialog tableUuid={table.uuid} onClose={() => setDialogOpen(false)} />
      )}
    </header>
  );
}
