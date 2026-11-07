import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { catalogQueryKeys } from "@/api/catalogQueryKeys";
import type { CreateGenericTableApiRequest } from "@/api/catalogTypes";
import { apiSend } from "@/api/client";
import { errorMessage } from "@/format";
import { genericTablesApiPath } from "@/lib/catalogPaths";
import { FormDialog } from "./FormDialog";
import { PropertiesEditor } from "./PropertiesEditor";
import { propertiesFromRows, type PropertyRow } from "./propertyRows";
import { TextField } from "./TextField";

interface Props {
  catalog: string;
  namespace: string[];
  onClose: () => void;
}

// Upstream has no form for this; the fields are the API's create request.
export function CreateGenericTableDialog({ catalog, namespace, onClose }: Props) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [format, setFormat] = useState("");
  const [baseLocation, setBaseLocation] = useState("");
  const [doc, setDoc] = useState("");
  const [rows, setRows] = useState<PropertyRow[]>([]);
  const [invalid, setInvalid] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: (body: CreateGenericTableApiRequest) =>
      apiSend("POST", genericTablesApiPath(catalog, namespace), body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: catalogQueryKeys.genericTables(catalog, namespace) });
      onClose();
    },
  });

  function submit() {
    const problem = name.trim() === "" ? "Name is required" : format.trim() === "" ? "Format is required" : null;
    setInvalid(problem);
    if (problem !== null) return;
    const body: CreateGenericTableApiRequest = {
      name: name.trim(),
      format: format.trim(),
      properties: propertiesFromRows(rows),
    };
    if (baseLocation.trim() !== "") body.base_location = baseLocation.trim();
    if (doc.trim() !== "") body.doc = doc.trim();
    create.mutate(body);
  }

  return (
    <FormDialog
      title="New generic table"
      description={
        <>
          Registers a non-Iceberg table in{" "}
          <span className="font-mono text-[13px]">{[catalog, ...namespace].join(" / ")}</span>.
        </>
      }
      submitLabel="Create"
      isPending={create.isPending}
      error={invalid ?? (create.isError ? errorMessage(create.error) : null)}
      onSubmit={submit}
      onClose={onClose}
    >
      <TextField label="Name" mono value={name} onChange={setName} />
      <TextField label="Format" mono placeholder="e.g. delta, csv" value={format} onChange={setFormat} />
      <TextField label="Base location (optional)" mono value={baseLocation} onChange={setBaseLocation} />
      <TextField label="Doc (optional)" value={doc} onChange={setDoc} />
      <PropertiesEditor rows={rows} onChange={setRows} />
    </FormDialog>
  );
}
