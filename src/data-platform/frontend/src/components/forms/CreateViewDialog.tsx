import { useMutation, useQueryClient } from "@tanstack/react-query";
import { TextArea } from "@retail-lakehouse/design-system";
import { useState } from "react";
import { catalogQueryKeys } from "@/api/catalogQueryKeys";
import type { CreateViewApiRequest } from "@/api/catalogTypes";
import { apiSend } from "@/api/client";
import { errorMessage } from "@/format";
import { viewsApiPath } from "@/lib/catalogPaths";
import { FormDialog } from "./FormDialog";
import { TextField } from "./TextField";

// The API requires a dialect; upstream's CreateViewModal defaults it to spark.
const DEFAULT_DIALECT = "spark";

interface Props {
  catalog: string;
  namespace: string[];
  onClose: () => void;
}

export function CreateViewDialog({ catalog, namespace, onClose }: Props) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [dialect, setDialect] = useState(DEFAULT_DIALECT);
  const [sql, setSql] = useState("");
  const [invalid, setInvalid] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: (body: CreateViewApiRequest) => apiSend("POST", viewsApiPath(catalog, namespace), body),
    // A write can fail after part of it landed, so the page refetches either way; the dialog
    // closes only on success and otherwise shows the API's message, which says what landed.
    onSettled: async (_data, error) => {
      await queryClient.invalidateQueries({ queryKey: catalogQueryKeys.views(catalog, namespace) });
      if (error === null) onClose();
    },
  });

  function submit() {
    const problem =
      name.trim() === ""
        ? "Name is required"
        : dialect.trim() === ""
          ? "Dialect is required"
          : sql.trim() === ""
            ? "SQL is required"
            : null;
    setInvalid(problem);
    if (problem !== null) return;
    create.mutate({ name: name.trim(), sql, dialect: dialect.trim() });
  }

  return (
    <FormDialog
      title="New view"
      description={
        <>
          Creates an Iceberg view in{" "}
          <span className="font-mono">{[catalog, ...namespace].join(" / ")}</span>.
        </>
      }
      submitLabel="Create"
      isPending={create.isPending}
      error={invalid ?? (create.isError ? errorMessage(create.error) : null)}
      onSubmit={submit}
      onClose={onClose}
    >
      <TextField label="Name" mono placeholder="my_view" value={name} onChange={setName} />
      <TextField
        label="Dialect"
        mono
        hint="The SQL dialect of the view, such as spark or trino."
        value={dialect}
        onChange={setDialect}
      />
      <TextArea
        label="SQL"
        className="min-h-36 font-mono"
        placeholder="SELECT * FROM my_table WHERE ..."
        value={sql}
        onChange={(event) => setSql(event.target.value)}
      />
    </FormDialog>
  );
}
