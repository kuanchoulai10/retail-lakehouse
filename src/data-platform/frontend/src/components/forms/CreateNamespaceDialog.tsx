import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { catalogQueryKeys } from "@/api/catalogQueryKeys";
import type { CreateNamespaceApiRequest } from "@/api/catalogTypes";
import { apiSend } from "@/api/client";
import { errorMessage } from "@/format";
import { namespacesApiPath } from "@/lib/catalogPaths";
import { FormDialog } from "./FormDialog";
import { PropertiesEditor } from "./PropertiesEditor";
import { propertiesFromRows, type PropertyRow } from "./propertyRows";
import { TextField } from "./TextField";

interface Props {
  catalog: string;
  parent: string[];
  onClose: () => void;
}

// Upstream splits the name on dots to make nested namespaces. Here the name is one part,
// so a dot stays part of the name ("a.b" is one namespace); nesting is done by creating
// the child on its parent's page.
export function CreateNamespaceDialog({ catalog, parent, onClose }: Props) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [location, setLocation] = useState("");
  const [rows, setRows] = useState<PropertyRow[]>([]);
  const [invalid, setInvalid] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: (body: CreateNamespaceApiRequest) =>
      apiSend("POST", namespacesApiPath(catalog, []), body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: catalogQueryKeys.namespaceLists(catalog) });
      onClose();
    },
  });

  function submit() {
    const problem = name.trim() === "" ? "Name is required" : null;
    setInvalid(problem);
    if (problem !== null) return;
    const properties = propertiesFromRows(rows);
    // As upstream: a "location" property typed in by hand wins over the Location field.
    const withLocation =
      location.trim() === "" ? properties : { location: location.trim(), ...properties };
    create.mutate({ namespace: [...parent, name.trim()], properties: withLocation });
  }

  return (
    <FormDialog
      title="New namespace"
      description={
        parent.length === 0 ? (
          <>
            Creates a top-level namespace in <span className="font-mono text-[13px]">{catalog}</span>.
          </>
        ) : (
          <>
            Creates a namespace inside{" "}
            <span className="font-mono text-[13px]">{[catalog, ...parent].join(" / ")}</span>.
          </>
        )
      }
      submitLabel="Create"
      isPending={create.isPending}
      error={invalid ?? (create.isError ? errorMessage(create.error) : null)}
      onSubmit={submit}
      onClose={onClose}
    >
      <TextField label="Name" mono placeholder="e.g. accounting" value={name} onChange={setName} />
      <TextField
        label="Location (optional)"
        mono
        placeholder="s3://bucket/path"
        value={location}
        onChange={setLocation}
      />
      <PropertiesEditor rows={rows} onChange={setRows} />
    </FormDialog>
  );
}
