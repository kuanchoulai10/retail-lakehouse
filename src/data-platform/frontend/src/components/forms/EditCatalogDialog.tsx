import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  getGetCatalogQueryKey,
  getListCatalogsQueryKey,
  updateCatalog,
} from "@/api/generated/catalogs/catalogs";
import type { CatalogApiResponse, UpdateCatalogApiRequest } from "@/api/generated/model";
import { Button } from "@retail-lakehouse/design-system";
import { isConflict, updateErrorMessage } from "@/lib/updateErrorMessage";
import { FormDialog } from "./FormDialog";
import { PropertiesEditor } from "./PropertiesEditor";
import { propertiesFromRows, rowsFromProperties } from "./propertyRows";
import { StorageConfigFields } from "./StorageConfigFields";
import { storageConfigRequest, storageFormError, storageFormFrom } from "./storageForm";
import { TextField } from "./TextField";

// Shown as its own field, so it is not repeated among the properties.
const BASE_LOCATION_KEY = "default-base-location";

interface Props {
  catalog: CatalogApiResponse;
  onClose: () => void;
}

// Edits what upstream's EditCatalogModal edits: base location, storage and properties.
// The connection of an EXTERNAL catalog is not editable, so no secret is ever filled in.
export function EditCatalogDialog({ catalog, onClose }: Props) {
  const queryClient = useQueryClient();
  const [baseLocation, setBaseLocation] = useState(catalog.default_base_location ?? "");
  const [storage, setStorage] = useState(() => storageFormFrom(catalog.storage_config));
  const [rows, setRows] = useState(() => {
    const rest = Object.fromEntries(
      Object.entries(catalog.properties).filter(([key]) => key !== BASE_LOCATION_KEY),
    );
    return rowsFromProperties(rest);
  });
  // The version the form was filled from. A refetch while the dialog is open must not move
  // it forward, or the save would pass the check and overwrite a change made meanwhile.
  const [loadedVersion] = useState(catalog.entity_version);
  const [invalid, setInvalid] = useState<string | null>(null);

  const refetchCatalog = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: getGetCatalogQueryKey(catalog.name) }),
      queryClient.invalidateQueries({ queryKey: getListCatalogsQueryKey() }),
    ]);

  const update = useMutation({
    mutationFn: (body: UpdateCatalogApiRequest) => updateCatalog(catalog.name, body),
    // A write can fail after part of it landed, so the page refetches either way; the dialog
    // closes only on success and otherwise shows the API's message, which says what landed.
    onSettled: async (_data, error) => {
      await refetchCatalog();
      if (error === null) onClose();
    },
  });

  function submit() {
    const problem =
      baseLocation.trim() === "" ? "Default base location is required" : storageFormError(storage);
    setInvalid(problem);
    if (problem !== null) return;
    update.mutate({
      entity_version: loadedVersion,
      default_base_location: baseLocation.trim(),
      properties: propertiesFromRows(rows),
      storage_config: storageConfigRequest(storage),
    });
  }

  function reload() {
    void refetchCatalog();
    onClose();
  }

  return (
    <FormDialog
      title="Edit catalog"
      description={
        <>
          Changes <span className="font-mono">{catalog.name}</span> as of
          the version you loaded.
        </>
      }
      submitLabel="Save"
      isPending={update.isPending}
      error={invalid ?? (update.isError ? updateErrorMessage(update.error, "catalog") : null)}
      errorAction={
        isConflict(update.error) ? (
          <Button type="button" styleType="outlined" size="small" onClick={reload}>
            Reload
          </Button>
        ) : undefined
      }
      onSubmit={submit}
      onClose={onClose}
    >
      <TextField label="Default base location" mono value={baseLocation} onChange={setBaseLocation} />
      <StorageConfigFields form={storage} onChange={setStorage} />
      <PropertiesEditor rows={rows} onChange={setRows} />
    </FormDialog>
  );
}
