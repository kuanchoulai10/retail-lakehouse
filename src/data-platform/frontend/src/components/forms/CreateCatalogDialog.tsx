import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { catalogQueryKeys } from "@/api/catalogQueryKeys";
import type { CatalogKind, CreateCatalogApiRequest } from "@/api/catalogTypes";
import { apiSend } from "@/api/client";
import { errorMessage } from "@/format";
import { catalogsApiPath } from "@/lib/catalogPaths";
import { ConnectionConfigFields } from "./ConnectionConfigFields";
import { connectionConfigRequest, connectionFormError, emptyConnectionForm } from "./connectionForm";
import { FormDialog } from "./FormDialog";
import { SelectField } from "./SelectField";
import { StorageConfigFields } from "./StorageConfigFields";
import { emptyStorageForm, storageConfigRequest, storageFormError } from "./storageForm";
import { TextField } from "./TextField";

const KIND_OPTIONS = [
  { value: "INTERNAL", label: "Internal" },
  { value: "EXTERNAL", label: "External" },
] as const;

export function CreateCatalogDialog({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [kind, setKind] = useState<CatalogKind>("INTERNAL");
  const [baseLocation, setBaseLocation] = useState("");
  const [storage, setStorage] = useState(emptyStorageForm);
  const [connection, setConnection] = useState(emptyConnectionForm);
  const [invalid, setInvalid] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: (body: CreateCatalogApiRequest) => apiSend("POST", catalogsApiPath(), body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: catalogQueryKeys.catalogs() });
      onClose();
    },
  });

  function validate(): string | null {
    if (name.trim() === "") return "Name is required";
    if (baseLocation.trim() === "") return "Default base location is required";
    return storageFormError(storage) ?? (kind === "EXTERNAL" ? connectionFormError(connection) : null);
  }

  function submit() {
    const problem = validate();
    setInvalid(problem);
    if (problem !== null) return;
    const body: CreateCatalogApiRequest = {
      name: name.trim(),
      type: kind,
      default_base_location: baseLocation.trim(),
      storage_config: storageConfigRequest(storage),
    };
    // An INTERNAL catalog must not carry a connection.
    if (kind === "EXTERNAL") body.connection_config = connectionConfigRequest(connection);
    create.mutate(body);
  }

  return (
    <FormDialog
      title="New catalog"
      description="Creates the catalog in Polaris and lets its catalog_admin role manage its content."
      submitLabel="Create"
      isPending={create.isPending}
      error={invalid ?? (create.isError ? errorMessage(create.error) : null)}
      onSubmit={submit}
      onClose={onClose}
    >
      <TextField label="Name" placeholder="e.g. prod" value={name} onChange={setName} />
      <SelectField label="Type" value={kind} options={[...KIND_OPTIONS]} onChange={setKind} />
      <TextField
        label="Default base location"
        mono
        placeholder="e.g. s3://bucket/prefix or file:///path"
        value={baseLocation}
        onChange={setBaseLocation}
      />
      <StorageConfigFields form={storage} onChange={setStorage} />
      {kind === "EXTERNAL" && <ConnectionConfigFields form={connection} onChange={setConnection} />}
    </FormDialog>
  );
}
