import { Banner, Select } from "@retail-lakehouse/design-system";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { SetTablePriorityApiRequestPriority, TableApiResponse } from "@/api/generated/model";
import { getGetTableQueryKey, getListTablesQueryKey, setTablePriority } from "@/api/generated/tables/tables";
import { errorMessage } from "@/format";
import { TABLE_PRIORITY_ITEMS } from "@/lib/tablePriorityItems";

interface Props {
  table: TableApiResponse;
}

// The priority maintenance runs this table at. Choosing a value saves it at once; the select shows
// the chosen value while the save and the refetch are in flight and falls back to the record's
// priority after a failed save. A dropped table's priority is read-only (the API refuses it).
export function TablePrioritySelect({ table }: Props) {
  const queryClient = useQueryClient();
  const save = useMutation({
    mutationFn: (priority: SetTablePriorityApiRequestPriority) => setTablePriority(table.uuid, { priority }),
    onSettled: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: getGetTableQueryKey(table.uuid) }),
        queryClient.invalidateQueries({ queryKey: getListTablesQueryKey() }),
      ]),
  });
  const shown = save.isPending ? save.variables : table.priority;
  return (
    <div className="flex flex-col gap-2">
      <Select
        label="Priority"
        hideLabel
        className="max-w-48"
        items={TABLE_PRIORITY_ITEMS}
        value={shown}
        disabled={table.status.toLowerCase() === "dropped"}
        onValueChange={(priority) => save.mutate(priority as SetTablePriorityApiRequestPriority)}
      />
      {save.isError && (
        <Banner type="negative" title={`Could not set the priority: ${errorMessage(save.error)}`} />
      )}
    </div>
  );
}
