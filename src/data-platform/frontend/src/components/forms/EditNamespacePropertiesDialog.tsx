import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { catalogQueryKeys } from "@/api/catalogQueryKeys";
import type { NamespaceApiResponse, UpdateNamespacePropertiesApiRequest } from "@/api/catalogTypes";
import { apiSend } from "@/api/client";
import { namespacePropertiesApiPath } from "@/lib/catalogPaths";
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
  const [rows, setRows] = useState(() => rowsFromProperties(namespace.properties));

  const update = useMutation({
    mutationFn: (body: UpdateNamespacePropertiesApiRequest) =>
      apiSend("PUT", namespacePropertiesApiPath(namespace.catalog, namespace.namespace), body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: catalogQueryKeys.namespace(namespace.catalog, namespace.namespace),
      });
      onClose();
    },
  });

  return (
    <FormDialog
      title="Edit properties"
      description={
        <>
          Sets and removes properties of{" "}
          <span className="font-mono text-[13px] text-foreground">
            {[namespace.catalog, ...namespace.namespace].join(" / ")}
          </span>
          .
        </>
      }
      submitLabel="Save"
      isPending={update.isPending}
      error={update.isError ? updateErrorMessage(update.error, "namespace") : null}
      onSubmit={() => update.mutate(propertyChanges(namespace.properties, rows))}
      onClose={onClose}
    >
      <PropertiesEditor rows={rows} onChange={setRows} />
    </FormDialog>
  );
}
