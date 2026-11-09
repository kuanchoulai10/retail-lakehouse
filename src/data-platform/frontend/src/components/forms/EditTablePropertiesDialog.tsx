import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { CatalogTableApiResponse, UpdateTablePropertiesApiRequest } from "@/api/generated/model";
import { getGetCatalogTableQueryKey, updateTableProperties } from "@/api/generated/tables/tables";
import { Button } from "@retail-lakehouse/design-system";
import { apiNamespace } from "@/lib/catalogPaths";
import { isConflict, updateErrorMessage } from "@/lib/updateErrorMessage";
import { FormDialog } from "./FormDialog";
import { PropertiesEditor } from "./PropertiesEditor";
import { propertyChanges, rowsFromProperties } from "./propertyRows";

interface Props {
  table: CatalogTableApiResponse;
  onClose: () => void;
}

// Sends only what changed, guarded by the uuid of the table the form was filled from: if the
// table was dropped and recreated meanwhile, the catalog answers 409 and the user reloads.
export function EditTablePropertiesDialog({ table, onClose }: Props) {
  const queryClient = useQueryClient();
  // Captured when the dialog opens; a refetch while it is open must not move the baseline or
  // the uuid forward, or the save would overwrite a change made meanwhile.
  const [loaded] = useState(table.properties);
  const [expectedUuid] = useState(table.uuid);
  const [rows, setRows] = useState(() => rowsFromProperties(loaded));
  const queryKey = getGetCatalogTableQueryKey(table.catalog, apiNamespace(table.namespace), table.name);

  const update = useMutation({
    mutationFn: (body: UpdateTablePropertiesApiRequest) =>
      updateTableProperties(table.catalog, apiNamespace(table.namespace), table.name, body),
    // A write can fail after part of it landed, so the page refetches either way; the dialog
    // closes only on success and otherwise shows the API's message, which says what landed.
    onSettled: async (_data, error) => {
      await queryClient.invalidateQueries({ queryKey });
      if (error === null) onClose();
    },
  });

  function reload() {
    void queryClient.invalidateQueries({ queryKey });
    onClose();
  }

  return (
    <FormDialog
      title="Edit properties"
      description={
        <>
          Sets and removes properties of{" "}
          <span className="font-mono">
            {[table.catalog, ...table.namespace, table.name].join(" / ")}
          </span>
          .
        </>
      }
      submitLabel="Save"
      isPending={update.isPending}
      error={update.isError ? updateErrorMessage(update.error, "table") : null}
      errorAction={
        isConflict(update.error) ? (
          <Button type="button" styleType="outlined" size="small" onClick={reload}>
            Reload
          </Button>
        ) : undefined
      }
      onSubmit={() => update.mutate({ expected_uuid: expectedUuid, ...propertyChanges(loaded, rows) })}
      onClose={onClose}
    >
      <PropertiesEditor rows={rows} onChange={setRows} />
    </FormDialog>
  );
}
