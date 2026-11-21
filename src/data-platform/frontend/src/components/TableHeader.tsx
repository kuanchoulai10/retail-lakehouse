import { Banner, Button } from "@retail-lakehouse/design-system";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import type { CatalogTableApiResponse, TableApiResponse } from "@/api/generated/model";
import { getListTableReconciliationsQueryKey } from "@/api/generated/table-reconciliations/table-reconciliations";
import { useTriggerTableReconciliation } from "@/api/generated/tables/tables";
import type { ActionItem } from "@/components/ActionsMenu";
import { PageHeader } from "@/components/PageHeader";
import { RunMaintenanceDialog } from "@/components/RunMaintenanceDialog";
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

const DISABLED_REASON = "Only a managed table can run maintenance";

// The workflow writes its record after the 202, so the first refetch is usually early.
const RECONCILE_REFRESH_DELAY_MS = 3000;

function averageFileSize(table: CatalogTableApiResponse): string {
  const { total_files_size: bytes, total_data_files: files } = table.summary;
  if (bytes === null || files === null || files === 0) return "avg —";
  return `avg ${formatBytes(bytes / files)} / file`;
}

// The same six numbers for every table, from the catalog; Run maintenance and Reconcile now only when maintenance manages
// it. The discovery policies alone decide whether it does, so there is no pause or include here.
// The maintenance actions live here, not in a child, so the phone overflow menu opens the same
// dialog as the buttons.
export function TableHeader({ table, managed, menuItems }: Props) {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [openCount, setOpenCount] = useState(0);
  const active = managed?.status.toLowerCase() === "managed";
  const refreshTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(refreshTimer.current), []);
  const reconcile = useTriggerTableReconciliation({
    mutation: {
      onSuccess: (_result, { tableUuid }) => {
        clearTimeout(refreshTimer.current);
        refreshTimer.current = setTimeout(
          () => queryClient.invalidateQueries({ queryKey: getListTableReconciliationsQueryKey(tableUuid) }),
          RECONCILE_REFRESH_DELAY_MS,
        );
      },
      onSettled: (_result, _error, { tableUuid }) =>
        queryClient.invalidateQueries({ queryKey: getListTableReconciliationsQueryKey(tableUuid) }),
    },
  });

  function openRunDialog() {
    setOpenCount((count) => count + 1);
    setDialogOpen(true);
  }

  const snapshot = currentSnapshot(table);
  const size = table.summary.total_files_size;
  const maintenanceItems: ActionItem[] =
    managed === null
      ? []
      : [
          {
            label: "Run maintenance",
            onSelect: openRunDialog,
            disabled: !active,
            ...(active ? {} : { description: DISABLED_REASON }),
          },
          {
            label: "Reconcile now",
            onSelect: () => reconcile.mutate({ tableUuid: managed.uuid }),
            disabled: reconcile.isPending,
          },
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
                disabled={reconcile.isPending}
                onClick={() => reconcile.mutate({ tableUuid: managed.uuid })}
              >
                Reconcile now
              </Button>
            </>
          )
        }
        actionItems={maintenanceItems}
        menuItems={menuItems}
      >
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
      {reconcile.isSuccess && (
        <Banner type="information" title="Reconciliation requested." className="mb-4" />
      )}
      {reconcile.isError && (
        <Banner
          type="negative"
          title={`Could not reconcile the table: ${errorMessage(reconcile.error)}`}
          className="mb-4"
        />
      )}
      {managed !== null && openCount > 0 && (
        <RunMaintenanceDialog
          key={openCount}
          tableUuid={managed.uuid}
          tablePriority={managed.priority}
          open={dialogOpen}
          onClose={() => setDialogOpen(false)}
        />
      )}
    </>
  );
}
