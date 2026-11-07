import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { catalogQueryKeys } from "@/api/catalogQueryKeys";
import type { ViewApiResponse } from "@/api/catalogTypes";
import { ApiError, apiGet, apiSend } from "@/api/client";
import { ActionsMenu } from "@/components/ActionsMenu";
import { CatalogObjectNotFound } from "@/components/CatalogObjectNotFound";
import { ConfirmDeleteDialog } from "@/components/ConfirmDeleteDialog";
import { PageHeader } from "@/components/PageHeader";
import { Panel } from "@/components/Panel";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { PropertiesPanel } from "@/components/PropertiesPanel";
import { SchemaFieldsPanel } from "@/components/SchemaFieldsPanel";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { errorMessage, formatTimestamp } from "@/format";
import { catalogObjectCrumbs } from "@/lib/catalogObjectCrumbs";
import { namespaceFromParam, namespacePath, viewApiPath } from "@/lib/catalogPaths";
import { useLeavingPage } from "@/lib/useLeavingPage";

// The fixed view page: SQL, schema, versions and properties. Polaris cannot rename or edit a
// view, so Actions holds Delete only.
// Keyed by the view, so leaving after a delete always unmounts it (see useLeavingPage).
export function ViewPage() {
  const { catalog = "", namespace: param = "", view: name = "" } = useParams();
  return <ViewDetails key={JSON.stringify([catalog, param, name])} catalog={catalog} parts={namespaceFromParam(param)} name={name} />;
}

interface ViewDetailsProps {
  catalog: string;
  parts: string[];
  name: string;
}

function ViewDetails({ catalog, parts, name }: ViewDetailsProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [deleting, setDeleting] = useState(false);
  const { leaving, leave } = useLeavingPage([catalogQueryKeys.view(catalog, parts, name)]);

  const view = useQuery({
    queryKey: catalogQueryKeys.view(catalog, parts, name),
    queryFn: () => apiGet<ViewApiResponse>(viewApiPath(catalog, parts, name)),
    enabled: !leaving,
  });
  const remove = useMutation({
    mutationFn: () => apiSend("DELETE", viewApiPath(catalog, parts, name)),
    onSuccess: async () => {
      leave();
      navigate(namespacePath(catalog, parts));
      await queryClient.invalidateQueries({ queryKey: catalogQueryKeys.views(catalog, parts), exact: true });
    },
  });

  if (view.isPending) return <PanelSkeleton label="Loading view…" />;
  if (view.isError) {
    if (view.error instanceof ApiError && view.error.status === 404) {
      return <CatalogObjectNotFound objectKind="view" catalog={catalog} namespace={parts} name={name} />;
    }
    return (
      <Alert variant="destructive">
        <AlertDescription>Could not load view: {errorMessage(view.error)}</AlertDescription>
      </Alert>
    );
  }

  const versions = [...view.data.versions].sort((a, b) => b.version_id - a.version_id);
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
        <span>View</span>
      </PageHeader>
      <div className="flex flex-col gap-6">
        <Panel title="SQL" actions={<span className={`${mono} text-muted-foreground`}>{view.data.dialect}</span>}>
          <pre className={`overflow-x-auto p-4 ${mono}`}>
            <code>{view.data.sql}</code>
          </pre>
        </Panel>
        <Panel title="Overview">
          <dl className="grid grid-cols-[10rem_1fr] gap-x-4 gap-y-2 px-4 py-3 text-sm">
            <dt className="text-muted-foreground">Location</dt>
            <dd className={`break-all ${mono}`}>{view.data.location}</dd>
            <dt className="text-muted-foreground">UUID</dt>
            <dd className={`break-all ${mono}`}>{view.data.uuid}</dd>
            <dt className="text-muted-foreground">Default namespace</dt>
            <dd className={mono}>{view.data.default_namespace.join(" / ") || "—"}</dd>
          </dl>
        </Panel>
        <SchemaFieldsPanel schema={view.data.schema} />
        <Panel title="Versions">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="px-4">Version</TableHead>
                <TableHead>
                  <span className="sr-only">Current</span>
                </TableHead>
                <TableHead>Created</TableHead>
                <TableHead>SQL</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {versions.map((version) => (
                <TableRow key={version.version_id}>
                  <TableCell className="px-4 tabular-nums">{version.version_id}</TableCell>
                  <TableCell>
                    {version.version_id === view.data.current_version_id && <Badge variant="outline">Current</Badge>}
                  </TableCell>
                  <TableCell className="tabular-nums">{formatTimestamp(new Date(version.timestamp_ms).toISOString())}</TableCell>
                  <TableCell className={`whitespace-normal break-all ${mono}`}>{version.sql}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Panel>
        <PropertiesPanel properties={view.data.properties} />
      </div>
      {deleting && (
        <ConfirmDeleteDialog
          open
          onOpenChange={(next) => !next && setDeleting(false)}
          objectKind="view"
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
