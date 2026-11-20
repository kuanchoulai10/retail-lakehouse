import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Banner, Button, CheckBox, Divider, ModalDialog, Select } from "@retail-lakehouse/design-system";
import { useState } from "react";
import {
  getListTableMaintenanceRunsQueryKey,
  useListTableMaintenanceRuns,
} from "@/api/generated/table-maintenance-runs/table-maintenance-runs";
import { triggerTableMaintenance } from "@/api/generated/tables/tables";
import type { TriggerTableMaintenanceApiRequestPriority } from "@/api/generated/model";
import { errorMessage } from "@/format";
import { isInFlightStatus } from "@/lib/isInFlightStatus";
import { TABLE_PRIORITY_ITEMS } from "@/lib/tablePriorityItems";

export const ALL_OPERATIONS = [
  "rewrite_data_files",
  "rewrite_manifests",
  "expire_snapshots",
  "remove_orphan_files",
];

interface Props {
  tableUuid: string;
  // The table's own priority. A run that keeps it sends none, so the backend uses the table's at plan time.
  tablePriority: string;
  initialOperations?: string[];
  open?: boolean;
  onClose: () => void;
}

export function RunMaintenanceDialog({
  tableUuid,
  tablePriority,
  initialOperations = ALL_OPERATIONS,
  open = true,
  onClose,
}: Props) {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<string[]>(initialOperations);
  const [priority, setPriority] = useState(tablePriority);
  // Read again on every open: the note must say what is in flight now, not what was when the dialog was last open.
  const newestRun = useListTableMaintenanceRuns(
    tableUuid,
    { limit: 1 },
    { query: { staleTime: 0, refetchOnMount: "always" } },
  );
  const inFlight = newestRun.data?.some((run) => isInFlightStatus(run.status)) ?? false;
  const run = useMutation({
    mutationFn: () =>
      triggerTableMaintenance(tableUuid, {
        operations: ALL_OPERATIONS.filter((op) => selected.includes(op)),
        ...(priority === tablePriority
          ? {}
          : { priority: priority as TriggerTableMaintenanceApiRequestPriority }),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: getListTableMaintenanceRunsQueryKey(tableUuid) });
      onClose();
    },
  });

  function toggle(operation: string) {
    setSelected((current) =>
      current.includes(operation) ? current.filter((o) => o !== operation) : [...current, operation],
    );
  }

  return (
    <ModalDialog
      isOpen={open}
      onOpenChange={(next) => !next && onClose()}
      title="Run maintenance"
      description="Runs on the whole table, ignoring thresholds"
      footer={
        <>
          <Button type="button" styleType="outlined" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="button"
            disabled={selected.length === 0 || run.isPending}
            onClick={() => run.mutate()}
          >
            Run
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-2">
        {ALL_OPERATIONS.map((operation) => (
          <CheckBox
            key={operation}
            id={`operation-${operation}`}
            label={operation}
            checked={selected.includes(operation)}
            onCheckedChange={() => toggle(operation)}
          />
        ))}
        <Divider className="my-2" />
        <Select
          label="Priority"
          items={TABLE_PRIORITY_ITEMS}
          value={priority}
          onValueChange={setPriority}
        />
        {inFlight && (
          <Banner
            type="information"
            title="A maintenance run is already in flight. Running now does not start another run: it raises that run's priority if you pick a higher one. The operations you pick are not added to it."
          />
        )}
        {run.isError && (
          <Banner type="negative" title={`Could not start maintenance: ${errorMessage(run.error)}`} />
        )}
      </div>
    </ModalDialog>
  );
}
