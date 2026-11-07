import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { apiSend } from "@/api/client";
import { invalidateTableState } from "@/api/invalidateTableState";
import type { TableApiResponse, TableMetadataApiResponse } from "@/api/types";
import { PageHeader } from "@/components/PageHeader";
import { RunMaintenanceDialog } from "@/components/RunMaintenanceDialog";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { errorMessage, formatBytes, formatCount, formatRelativeTime } from "@/format";

interface Props {
  table: TableApiResponse;
  metadata: TableMetadataApiResponse | undefined;
}

const DISABLED_REASON = "Only an active table can run maintenance";

function averageFileSize(metadata: TableMetadataApiResponse): string {
  const { total_files_size_bytes: bytes, total_data_files: files } = metadata;
  if (bytes === null || files === null || files === 0) return "avg —";
  return `avg ${formatBytes(bytes / files)} / file`;
}

export function TableHeader({ table, metadata }: Props) {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [openCount, setOpenCount] = useState(0);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const paused = table.status.toLowerCase() === "paused";
  const active = table.status.toLowerCase() === "active";
  const toggle = useMutation({
    mutationFn: () => apiSend("POST", `/v1/tables/${table.uuid}/${paused ? "resume" : "pause"}`),
    onSuccess: () => invalidateTableState(queryClient, table.uuid),
  });

  const actions = (
    <>
      <Button
        ref={triggerRef}
        type="button"
        disabled={!active}
        title={active ? undefined : DISABLED_REASON}
        aria-describedby={active ? undefined : "run-maintenance-reason"}
        onClick={() => {
          setOpenCount((count) => count + 1);
          setDialogOpen(true);
        }}
      >
        Run maintenance
      </Button>
      {!active && (
        <span id="run-maintenance-reason" className="sr-only">
          {DISABLED_REASON}
        </span>
      )}
      <Button
        type="button"
        variant="outline"
        disabled={toggle.isPending}
        onClick={() => toggle.mutate()}
      >
        {paused ? "Resume" : "Pause"}
      </Button>
    </>
  );

  return (
    <>
      <PageHeader
        title={`${table.catalog}.${table.namespace}.${table.table}`}
        breadcrumb={`${table.catalog} / ${table.namespace}`}
        actions={actions}
      >
        <StatusBadge status={table.status} />
        <span>Preset: {table.source_preset_id ?? "—"}</span>
        <span>Rule: {table.matched_rule_id ?? "—"}</span>
        {metadata && (
          <>
            <span className="tabular-nums">{formatCount(metadata.total_records)} rows</span>
            <span className="tabular-nums">{formatCount(metadata.total_data_files)} data files</span>
            <span className="tabular-nums">
              {metadata.total_files_size_bytes === null
                ? "—"
                : formatBytes(metadata.total_files_size_bytes)}
            </span>
            <span className="tabular-nums">{averageFileSize(metadata)}</span>
            <span className="tabular-nums">{formatCount(metadata.snapshot_count)} snapshots</span>
            <span>last commit {formatRelativeTime(metadata.last_committed_at)}</span>
          </>
        )}
      </PageHeader>
      {toggle.isError && (
        <p role="alert" className="mb-4 text-sm text-destructive">
          Could not change the table: {errorMessage(toggle.error)}
        </p>
      )}
      {openCount > 0 && (
        <RunMaintenanceDialog
          key={openCount}
          tableUuid={table.uuid}
          open={dialogOpen}
          returnFocusTo={triggerRef}
          onClose={() => setDialogOpen(false)}
        />
      )}
    </>
  );
}
