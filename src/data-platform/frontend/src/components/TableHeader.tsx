import { Banner, Button } from "@retail-lakehouse/design-system";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { CatalogTableApiResponse } from "@/api/catalogTypes";
import { apiSend } from "@/api/client";
import { invalidateTableState } from "@/api/invalidateTableState";
import type { TableApiResponse } from "@/api/types";
import type { ActionItem } from "@/components/ActionsMenu";
import { PageHeader } from "@/components/PageHeader";
import { RunMaintenanceDialog } from "@/components/RunMaintenanceDialog";
import { StatusBadge } from "@/components/StatusBadge";
import { errorMessage, formatBytes, formatCount, formatRelativeTime } from "@/format";
import { catalogObjectCrumbs } from "@/lib/catalogObjectCrumbs";
import { currentSnapshot } from "@/lib/currentSnapshot";

interface Props {
  table: CatalogTableApiResponse;
  // Maintenance's record when it manages the table; null otherwise.
  managed: TableApiResponse | null;
  // The Actions menu's items, shown on every table.
  menuItems: ActionItem[];
}

const DISABLED_REASON = "Only an active table can run maintenance";

function averageFileSize(table: CatalogTableApiResponse): string {
  const { total_files_size: bytes, total_data_files: files } = table.summary;
  if (bytes === null || files === null || files === 0) return "avg —";
  return `avg ${formatBytes(bytes / files)} / file`;
}

// Numbers come from the catalog; Pause/Resume and Run maintenance only when maintenance manages it.
// The maintenance actions live here, not in a child, so the phone overflow menu opens the same
// dialog and runs the same toggle as the buttons.
export function TableHeader({ table, managed, menuItems }: Props) {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [openCount, setOpenCount] = useState(0);
  const status = managed?.status.toLowerCase();
  const paused = status === "paused";
  const active = status === "active";
  const toggle = useMutation({
    mutationFn: (uuid: string) => apiSend("POST", `/v1/tables/${uuid}/${paused ? "resume" : "pause"}`),
    onSuccess: (_result, uuid) => invalidateTableState(queryClient, uuid),
  });

  function openRunDialog() {
    setOpenCount((count) => count + 1);
    setDialogOpen(true);
  }

  const snapshot = currentSnapshot(table);
  const size = table.summary.total_files_size;
  const toggleLabel = paused ? "Resume" : "Pause";
  const maintenanceItems: ActionItem[] =
    managed === null
      ? []
      : [
          { label: "Run maintenance", onSelect: openRunDialog, disabled: !active },
          { label: toggleLabel, onSelect: () => toggle.mutate(managed.uuid), disabled: toggle.isPending },
        ];

  return (
    <>
      <PageHeader
        title={table.name}
        breadcrumbs={catalogObjectCrumbs(table.catalog, table.namespace, table.name)}
        actions={
          managed === null ? undefined : (
            <>
              <Button
                type="button"
                disabled={!active}
                title={active ? undefined : DISABLED_REASON}
                aria-describedby={active ? undefined : "run-maintenance-reason"}
                onClick={openRunDialog}
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
                styleType="outlined"
                disabled={toggle.isPending}
                onClick={() => toggle.mutate(managed.uuid)}
              >
                {toggleLabel}
              </Button>
            </>
          )
        }
        actionItems={maintenanceItems}
        menuItems={menuItems}
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
      {toggle.isError && (
        <Banner
          type="negative"
          title={`Could not change the table: ${errorMessage(toggle.error)}`}
          className="mb-4"
        />
      )}
      {managed !== null && openCount > 0 && (
        <RunMaintenanceDialog
          key={openCount}
          tableUuid={managed.uuid}
          open={dialogOpen}
          onClose={() => setDialogOpen(false)}
        />
      )}
    </>
  );
}
