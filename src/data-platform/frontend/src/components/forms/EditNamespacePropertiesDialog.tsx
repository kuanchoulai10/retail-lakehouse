import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { NamespaceApiResponse, UpdateNamespacePropertiesApiRequest } from "@/api/generated/model";
import {
  getGetNamespaceQueryKey,
  updateNamespaceProperties,
} from "@/api/generated/namespaces/namespaces";
import { apiNamespace } from "@/lib/catalogPaths";
import { updateErrorMessage } from "@/lib/updateErrorMessage";
import { FormDialog } from "./FormDialog";
import { PropertiesEditor } from "./PropertiesEditor";
import { propertyChanges, rowsFromProperties } from "./propertyRows";

interface Props {
  namespace: NamespaceApiResponse;
  onClose: () => void;
}

// Sends only what changed: set keys as updates, dropped keys as removals.
export function EditNamespacePropertiesDialog({ namespace, onClose }: Props) {
  const queryClient = useQueryClient();
  // The properties the form was filled from; a refetch while the dialog is open must not
  // change what the edit is diffed against, or keys added meanwhile would be removed.
  const [loaded] = useState(namespace.properties);
  const [rows, setRows] = useState(() => rowsFromProperties(loaded));

  const update = useMutation({
    mutationFn: (body: UpdateNamespacePropertiesApiRequest) =>
      updateNamespaceProperties(namespace.catalog, apiNamespace(namespace.namespace), body),
    // A write can fail after part of it landed, so the page refetches either way; the dialog
    // closes only on success and otherwise shows the API's message, which says what landed.
    onSettled: async (_data, error) => {
      await queryClient.invalidateQueries({
        queryKey: getGetNamespaceQueryKey(namespace.catalog, apiNamespace(namespace.namespace)),
      });
      if (error === null) onClose();
    },
  });

  return (
    <FormDialog
      title="Edit properties"
      description={
        <>
          Sets and removes properties of{" "}
          <span className="font-mono">
            {[namespace.catalog, ...namespace.namespace].join(" / ")}
          </span>
          .
        </>
      }
      submitLabel="Save"
      isPending={update.isPending}
      error={update.isError ? updateErrorMessage(update.error, "namespace") : null}
      onSubmit={() => update.mutate(propertyChanges(loaded, rows))}
      onClose={onClose}
    >
      <PropertiesEditor rows={rows} onChange={setRows} />
    </FormDialog>
  );
}
