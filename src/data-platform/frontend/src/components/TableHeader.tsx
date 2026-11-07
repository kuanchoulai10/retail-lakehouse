import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState, type ReactNode } from "react";
import type { CatalogTableApiResponse } from "@/api/catalogTypes";
import { apiSend } from "@/api/client";
import { invalidateTableState } from "@/api/invalidateTableState";
import type { TableApiResponse } from "@/api/types";
import { PageHeader } from "@/components/PageHeader";
import { RunMaintenanceDialog } from "@/components/RunMaintenanceDialog";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { errorMessage, formatBytes, formatCount, formatRelativeTime } from "@/format";
import { catalogObjectCrumbs } from "@/lib/catalogObjectCrumbs";
import { currentSnapshot } from "@/lib/currentSnapshot";

interface Props {
  table: CatalogTableApiResponse;
  // Maintenance's record when it manages the table; null otherwise.
  managed: TableApiResponse | null;
  // The Actions menu, shown on every table.
  menu: ReactNode;
}

const DISABLED_REASON = "Only an active table can run maintenance";

function averageFileSize(table: CatalogTableApiResponse): string {
  const { total_files_size: bytes, total_data_files: files } = table.summary;
  if (bytes === null || files === null || files === 0) return "avg —";
  return `avg ${formatBytes(bytes / files)} / file`;
}

function MaintenanceActions({ managed }: { managed: TableApiResponse }) {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [openCount, setOpenCount] = useState(0);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const paused = managed.status.toLowerCase() === "paused";
  const active = managed.status.toLowerCase() === "active";
  const toggle = useMutation({
    mutationFn: () => apiSend("POST", `/v1/tables/${managed.uuid}/${paused ? "resume" : "pause"}`),
    onSuccess: () => invalidateTableState(queryClient, managed.uuid),
  });

  return (
    <>
      {toggle.isError && (
        <p role="alert" className="text-sm text-destructive">
          Could not change the table: {errorMessage(toggle.error)}
        </p>
      )}
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
      <Button type="button" variant="outline" disabled={toggle.isPending} onClick={() => toggle.mutate()}>
        {paused ? "Resume" : "Pause"}
      </Button>
      {openCount > 0 && (
        <RunMaintenanceDialog
          key={openCount}
          tableUuid={managed.uuid}
          open={dialogOpen}
          returnFocusTo={triggerRef}
          onClose={() => setDialogOpen(false)}
        />
      )}
    </>
  );
}

// Numbers come from the catalog; Pause/Resume and Run maintenance only when maintenance manages it.
export function TableHeader({ table, managed, menu }: Props) {
  const snapshot = currentSnapshot(table);
  const size = table.summary.total_files_size;
  return (
    <PageHeader
      title={table.name}
      breadcrumbs={catalogObjectCrumbs(table.catalog, table.namespace, table.name)}
      actions={
        <>
          {managed !== null && <MaintenanceActions managed={managed} />}
          {menu}
        </>
      }
    >
      {managed !== null && (
        <>
          <StatusBadge status={managed.status} />
          <span>Preset: {managed.source_preset_id ?? "—"}</span>
          <span>Rule: {managed.matched_rule_id ?? "—"}</span>
        </>
      )}
      <span className="tabular-nums">{formatCount(table.summary.total_records)} rows</span>
      <span className="tabular-nums">{formatCount(table.summary.total_data_files)} data files</span>
      <span className="tabular-nums">{size === null ? "—" : formatBytes(size)}</span>
      <span className="tabular-nums">{averageFileSize(table)}</span>
      <span className="tabular-nums">{formatCount(table.snapshots.length)} snapshots</span>
      <span>
        last commit{" "}
        {formatRelativeTime(snapshot === undefined ? null : new Date(snapshot.timestamp_ms).toISOString())}
      </span>
    </PageHeader>
  );
}
