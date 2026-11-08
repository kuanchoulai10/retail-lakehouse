import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router";
import { catalogQueryKeys } from "@/api/catalogQueryKeys";
import type {
  CatalogTableApiResponse,
  RenameTableApiRequest,
  TableIdentifierApiResponse,
} from "@/api/catalogTypes";
import { apiSend } from "@/api/client";
import { errorMessage } from "@/format";
import { tablePath, tableRenameApiPath } from "@/lib/catalogPaths";
import { FormDialog } from "./FormDialog";
import { NamespacePartsField } from "./NamespacePartsField";
import { TextField } from "./TextField";

interface Props {
  table: CatalogTableApiResponse;
  // The tab the page shows, kept across the move to the new URL.
  tab: string;
  // Called before navigating to the new URL, so the page stops loading the old name.
  onLeave: () => void;
  onClose: () => void;
}

function validationError(parts: string[], name: string, table: CatalogTableApiResponse): string | null {
  if (name.trim() === "") return "Name is required";
  if (parts.some((part) => part.trim() === "")) return "Every namespace level needs a name";
  const unchanged =
    name.trim() === table.name &&
    parts.length === table.namespace.length &&
    parts.every((part, index) => part.trim() === table.namespace[index]);
  return unchanged ? "Change the name or the namespace" : null;
}

// Renames the table or moves it to another namespace of the same catalog, then shows it at
// the URL the catalog answers with.
export function RenameTableDialog({ table, tab, onLeave, onClose }: Props) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [parts, setParts] = useState(table.namespace);
  const [name, setName] = useState(table.name);
  const [invalid, setInvalid] = useState<string | null>(null);

  const rename = useMutation({
    mutationFn: (body: RenameTableApiRequest) =>
      apiSend<TableIdentifierApiResponse>("POST", tableRenameApiPath(table.catalog, table.namespace, table.name), body),
    // The page stops loading the old name and drops its query when it unmounts (it is keyed by
    // the table's path, so the new URL mounts a fresh page and this dialog goes with the old
    // one). The namespace listings of both ends are refetched, and the source's even when the
    // rename fails, so a list never shows a state the catalog may no longer hold.
    onSuccess: (moved) => {
      onLeave();
      navigate(tablePath(moved.catalog, moved.namespace, moved.name, tab));
    },
    onSettled: async (moved) => {
      const namespaces = moved === undefined ? [table.namespace] : [table.namespace, moved.namespace];
      await Promise.all(
        namespaces.map((namespace) =>
          queryClient.invalidateQueries({ queryKey: catalogQueryKeys.tables(table.catalog, namespace) }),
        ),
      );
    },
  });

  function submit() {
    const problem = validationError(parts, name, table);
    setInvalid(problem);
    if (problem !== null) return;
    rename.mutate({ target_namespace: parts.map((part) => part.trim()), target_name: name.trim() });
  }

  return (
    <FormDialog
      title="Rename table"
      description={
        <>
          Renames <span className="font-mono">{[table.catalog, ...table.namespace, table.name].join(" / ")}</span>{" "}
          or moves it to another namespace of the catalog.
        </>
      }
      submitLabel="Rename"
      isPending={rename.isPending}
      error={invalid ?? (rename.isError ? errorMessage(rename.error) : null)}
      onSubmit={submit}
      onClose={onClose}
    >
      <NamespacePartsField parts={parts} onChange={setParts} />
      <TextField label="Name" mono value={name} onChange={setName} />
    </FormDialog>
  );
}
