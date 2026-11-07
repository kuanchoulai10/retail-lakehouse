import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { catalogQueryKeys } from "@/api/catalogQueryKeys";
import type { GenericTableApiResponse } from "@/api/catalogTypes";
import { ApiError, apiGet, apiSend } from "@/api/client";
import { ActionsMenu } from "@/components/ActionsMenu";
import { CatalogObjectNotFound } from "@/components/CatalogObjectNotFound";
import { ConfirmDeleteDialog } from "@/components/ConfirmDeleteDialog";
import { PageHeader } from "@/components/PageHeader";
import { Panel } from "@/components/Panel";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { PropertiesPanel } from "@/components/PropertiesPanel";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { errorMessage } from "@/format";
import { catalogObjectCrumbs } from "@/lib/catalogObjectCrumbs";
import { genericTableApiPath, namespaceFromParam, namespacePath } from "@/lib/catalogPaths";
import { useLeavingPage } from "@/lib/useLeavingPage";

// The fixed generic table page. A generic table has no schema, snapshots or uuid, and Polaris
// cannot rename or edit it, so Actions holds Delete only.
// Keyed by the generic table, so leaving after a delete always unmounts it (see useLeavingPage).
export function GenericTablePage() {
  const { catalog = "", namespace: param = "", name = "" } = useParams();
  return <GenericTableView key={JSON.stringify([catalog, param, name])} catalog={catalog} parts={namespaceFromParam(param)} name={name} />;
}

interface GenericTableViewProps {
  catalog: string;
  parts: string[];
  name: string;
}

function GenericTableView({ catalog, parts, name }: GenericTableViewProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [deleting, setDeleting] = useState(false);
  const { leaving, leave } = useLeavingPage([catalogQueryKeys.genericTable(catalog, parts, name)]);

  const genericTable = useQuery({
    queryKey: catalogQueryKeys.genericTable(catalog, parts, name),
    queryFn: () => apiGet<GenericTableApiResponse>(genericTableApiPath(catalog, parts, name)),
    enabled: !leaving,
  });
  const remove = useMutation({
    mutationFn: () => apiSend("DELETE", genericTableApiPath(catalog, parts, name)),
    onSuccess: async () => {
      leave();
      navigate(namespacePath(catalog, parts));
      await queryClient.invalidateQueries({
        queryKey: catalogQueryKeys.genericTables(catalog, parts),
        exact: true,
      });
    },
  });

  if (genericTable.isPending) return <PanelSkeleton label="Loading generic table…" />;
  if (genericTable.isError) {
    if (genericTable.error instanceof ApiError && genericTable.error.status === 404) {
      return <CatalogObjectNotFound objectKind="generic table" catalog={catalog} namespace={parts} name={name} />;
    }
    return (
      <Alert variant="destructive">
        <AlertDescription>Could not load generic table: {errorMessage(genericTable.error)}</AlertDescription>
      </Alert>
    );
  }

  const { format, base_location: location, doc, properties } = genericTable.data;
  const mono = "font-mono text-[13px]";

  return (
    <section>
      <PageHeader
        title={name}
        breadcrumbs={catalogObjectCrumbs(catalog, parts, name)}
        actions={
          <ActionsMenu
            items={[
              {
                label: "Delete",
                onSelect: () => {
                  remove.reset();
                  setDeleting(true);
                },
              },
            ]}
          />
        }
      >
        <span>Generic table</span>
      </PageHeader>
      <div className="flex flex-col gap-6">
        <Panel title="Overview">
          <dl className="grid grid-cols-[10rem_1fr] gap-x-4 gap-y-2 px-4 py-3 text-sm">
            <dt className="text-muted-foreground">Format</dt>
            <dd className={mono}>{format}</dd>
            <dt className="text-muted-foreground">Location</dt>
            <dd className={`break-all ${mono}`}>{location ?? "—"}</dd>
            <dt className="text-muted-foreground">Doc</dt>
            <dd>{doc ?? "—"}</dd>
          </dl>
        </Panel>
        <PropertiesPanel properties={properties} />
      </div>
      {deleting && (
        <ConfirmDeleteDialog
          open
          onOpenChange={(next) => !next && setDeleting(false)}
          objectKind="generic table"
          objectName={name}
          fullPath={[catalog, ...parts, name].join(" / ")}
          isPending={remove.isPending}
          error={remove.error}
          onConfirm={() => remove.mutate()}
        />
      )}
    </section>
  );
}
