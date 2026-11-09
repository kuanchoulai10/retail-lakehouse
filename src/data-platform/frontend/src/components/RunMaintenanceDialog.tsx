import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Banner, Button, CheckBox, ModalDialog } from "@retail-lakehouse/design-system";
import { useState } from "react";
import { getListTableMaintenanceRunsQueryKey } from "@/api/generated/table-maintenance-runs/table-maintenance-runs";
import { getGetTableHealthQueryKey, triggerTableMaintenance } from "@/api/generated/tables/tables";
import { errorMessage } from "@/format";

export const ALL_OPERATIONS = [
  "rewrite_data_files",
  "rewrite_manifests",
  "expire_snapshots",
  "remove_orphan_files",
];

interface Props {
  tableUuid: string;
  initialOperations?: string[];
  open?: boolean;
  onClose: () => void;
}

export function RunMaintenanceDialog({
  tableUuid,
  initialOperations = ALL_OPERATIONS,
  open = true,
  onClose,
}: Props) {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<string[]>(initialOperations);
  const run = useMutation({
    mutationFn: () =>
      triggerTableMaintenance(tableUuid, {
        operations: ALL_OPERATIONS.filter((op) => selected.includes(op)),
      }),
    onSuccess: async () => {
      await Promise.all(
        [getListTableMaintenanceRunsQueryKey(tableUuid), getGetTableHealthQueryKey(tableUuid)].map((queryKey) =>
          queryClient.invalidateQueries({ queryKey }),
        ),
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
        {run.isError && (
          <Banner type="negative" title={`Could not start maintenance: ${errorMessage(run.error)}`} />
        )}
      </div>
    </ModalDialog>
  );
}
