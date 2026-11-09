import {
  Badge,
  Banner,
  createDataTableColumnHelper,
  DataTable,
  Panel,
} from "@retail-lakehouse/design-system";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { ApiError } from "@/api/apiError";
import type { ViewVersionApiResponse } from "@/api/generated/model";
import { deleteView, getGetViewQueryKey, getListViewsQueryKey, useGetView } from "@/api/generated/views/views";
import { CatalogObjectNotFound } from "@/components/CatalogObjectNotFound";
import { ConfirmDeleteDialog } from "@/components/ConfirmDeleteDialog";
import { PageHeader } from "@/components/PageHeader";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { PropertiesPanel } from "@/components/PropertiesPanel";
import { SchemaFieldsPanel } from "@/components/SchemaFieldsPanel";
import { errorMessage, formatTimestamp } from "@/format";
import { catalogObjectCrumbs } from "@/lib/catalogObjectCrumbs";
import { apiNamespace, namespaceFromParam, namespacePath } from "@/lib/catalogPaths";
import { useLeavingPage } from "@/lib/useLeavingPage";

const versionColumn = createDataTableColumnHelper<ViewVersionApiResponse>();

function versionColumnsFor(currentVersionId: number) {
  return versionColumn.columns([
    versionColumn.accessor("version_id", {
      header: "Version",
      enableSorting: false,
      cell: (info) => <span className="tabular-nums">{info.getValue()}</span>,
    }),
    versionColumn.display({
      id: "current",
      header: () => <span className="sr-only">Current</span>,
      cell: (info) => (info.row.original.version_id === currentVersionId ? <Badge>Current</Badge> : null),
    }),
    versionColumn.accessor("timestamp_ms", {
      header: "Created",
      enableSorting: false,
      cell: (info) => (
        <span className="tabular-nums whitespace-nowrap">{formatTimestamp(new Date(info.getValue()).toISOString())}</span>
      ),
    }),
    versionColumn.accessor("sql", {
      header: "SQL",
      enableSorting: false,
      cell: (info) => <span className="type-code block min-w-48 break-all">{info.getValue()}</span>,
    }),
  ]);
}

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
  const ns = apiNamespace(parts);
  const { leaving, leave } = useLeavingPage([getGetViewQueryKey(catalog, ns, name)]);

  const view = useGetView(catalog, ns, name, { query: { enabled: !leaving } });
  const remove = useMutation({
    mutationFn: () => deleteView(catalog, ns, name),
    onSuccess: async () => {
      leave();
      navigate(namespacePath(catalog, parts));
      await queryClient.invalidateQueries({ queryKey: getListViewsQueryKey(catalog, ns), exact: true });
    },
  });

  if (view.isPending) return <PanelSkeleton label="Loading view…" />;
  if (view.isError) {
    if (view.error instanceof ApiError && view.error.status === 404) {
      return <CatalogObjectNotFound objectKind="view" catalog={catalog} namespace={parts} name={name} />;
    }
    return <Banner type="negative" title={`Could not load view: ${errorMessage(view.error)}`} />;
  }

  const versions = [...view.data.versions].sort((a, b) => b.version_id - a.version_id);
  const mono = "type-code";
  const versionColumns = versionColumnsFor(view.data.current_version_id);

  return (
    <section>
      <PageHeader
        title={name}
        breadcrumbs={catalogObjectCrumbs(catalog, parts, name)}
        menuItems={[
          {
            label: "Delete",
            destructive: true,
            onSelect: () => {
              remove.reset();
              setDeleting(true);
            },
          },
        ]}
      >
        <span>View</span>
      </PageHeader>
      <div className="flex flex-col gap-6">
        <Panel title="SQL" actions={<span className={`${mono} text-on-surface-variant`}>{view.data.dialect}</span>}>
          <pre className={`overflow-x-auto rounded-md bg-surface p-3 ${mono}`}>
            <code>{view.data.sql}</code>
          </pre>
        </Panel>
        <Panel title="Overview">
          <dl className="grid grid-cols-1 gap-x-4 gap-y-1 sm:grid-cols-[10rem_1fr] sm:gap-y-2">
            <dt className="text-on-surface-variant">Location</dt>
            <dd className={`break-all ${mono}`}>{view.data.location}</dd>
            <dt className="text-on-surface-variant">UUID</dt>
            <dd className={`break-all ${mono}`}>{view.data.uuid}</dd>
            <dt className="text-on-surface-variant">Default namespace</dt>
            <dd className={mono}>{view.data.default_namespace.join(" / ") || "—"}</dd>
          </dl>
        </Panel>
        <SchemaFieldsPanel schema={view.data.schema} />
        <Panel title="Versions">
          <DataTable
            caption="View versions, newest first"
            columns={versionColumns}
            data={versions}
            getRowId={(version) => String(version.version_id)}
          />
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
