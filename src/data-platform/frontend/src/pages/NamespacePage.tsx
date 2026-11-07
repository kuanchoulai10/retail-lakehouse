import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { catalogQueryKeys } from "@/api/catalogQueryKeys";
import type {
  NamespaceApiResponse,
  NamespaceSummaryApiResponse,
  TableIdentifierApiResponse,
} from "@/api/catalogTypes";
import { apiGet, apiSend } from "@/api/client";
import { ActionsMenu } from "@/components/ActionsMenu";
import type { Crumb } from "@/components/Breadcrumbs";
import { ConfirmDeleteDialog } from "@/components/ConfirmDeleteDialog";
import { CreateNamespaceDialog } from "@/components/forms/CreateNamespaceDialog";
import { EditNamespacePropertiesDialog } from "@/components/forms/EditNamespacePropertiesDialog";
import { NewNamespaceObjectDialog } from "@/components/forms/NewNamespaceObjectDialog";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { PropertiesPanel } from "@/components/PropertiesPanel";
import { ResourceListPage } from "@/components/ResourceListPage";
import { ResourceSection } from "@/components/ResourceSection";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { errorMessage } from "@/format";
import {
  catalogPath,
  catalogsPath,
  genericTableApiPath,
  genericTablePath,
  genericTablesApiPath,
  namespaceApiPath,
  namespaceFromParam,
  namespacePath,
  namespacesApiPath,
  tableApiPath,
  tablePath,
  tablesApiPath,
  viewApiPath,
  viewPath,
  viewsApiPath,
} from "@/lib/catalogPaths";

type ObjectType = "table" | "view" | "generic table";

interface ObjectRow {
  type: ObjectType;
  name: string;
}

const TYPE_LABEL: Record<ObjectType, string> = {
  table: "Table",
  view: "View",
  "generic table": "Generic table",
};

type Dialog = "edit" | "delete" | null;

function lastPart(parts: string[]): string {
  return parts[parts.length - 1] ?? "";
}

function breadcrumbs(catalog: string, parts: string[]): Crumb[] {
  return [
    { label: "Catalogs", to: catalogsPath() },
    { label: catalog, to: catalogPath(catalog) },
    ...parts.map((part, index) => ({ label: part, to: namespacePath(catalog, parts.slice(0, index + 1)) })),
  ];
}

export function NamespacePage() {
  const { catalog = "", namespace: param = "" } = useParams();
  const parts = namespaceFromParam(param);
  const parent = parts.slice(0, -1);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [dialog, setDialog] = useState<Dialog>(null);

  const namespace = useQuery({
    queryKey: catalogQueryKeys.namespace(catalog, parts),
    queryFn: () => apiGet<NamespaceApiResponse>(namespaceApiPath(catalog, parts)),
  });
  const children = useQuery({
    queryKey: catalogQueryKeys.namespaces(catalog, parts),
    queryFn: () => apiGet<NamespaceSummaryApiResponse[]>(namespacesApiPath(catalog, parts)),
  });
  const tables = useQuery({
    queryKey: catalogQueryKeys.tables(catalog, parts),
    queryFn: () => apiGet<TableIdentifierApiResponse[]>(tablesApiPath(catalog, parts)),
  });
  const views = useQuery({
    queryKey: catalogQueryKeys.views(catalog, parts),
    queryFn: () => apiGet<TableIdentifierApiResponse[]>(viewsApiPath(catalog, parts)),
  });
  const genericTables = useQuery({
    queryKey: catalogQueryKeys.genericTables(catalog, parts),
    queryFn: () => apiGet<TableIdentifierApiResponse[]>(genericTablesApiPath(catalog, parts)),
  });

  const removeChild = useMutation({
    mutationFn: (row: NamespaceSummaryApiResponse) => apiSend("DELETE", namespaceApiPath(catalog, row.namespace)),
    onSuccess: async (_result, row) => {
      queryClient.removeQueries({ queryKey: catalogQueryKeys.namespace(catalog, row.namespace) });
      await queryClient.invalidateQueries({ queryKey: catalogQueryKeys.namespaceLists(catalog) });
    },
  });
  const removeObject = useMutation({
    mutationFn: (row: ObjectRow) => {
      switch (row.type) {
        case "table":
          return apiSend("DELETE", tableApiPath(catalog, parts, row.name));
        case "view":
          return apiSend("DELETE", viewApiPath(catalog, parts, row.name));
        case "generic table":
          return apiSend("DELETE", genericTableApiPath(catalog, parts, row.name));
      }
    },
    onSuccess: (_result, row) => {
      const keys = {
        table: catalogQueryKeys.tables(catalog, parts),
        view: catalogQueryKeys.views(catalog, parts),
        "generic table": catalogQueryKeys.genericTables(catalog, parts),
      };
      return queryClient.invalidateQueries({ queryKey: keys[row.type] });
    },
  });
  const removeSelf = useMutation({
    mutationFn: () => apiSend("DELETE", namespaceApiPath(catalog, parts)),
    // Leave the page first, then drop what this page loaded, so nothing refetches the
    // namespace that is gone; only the parent's list is refetched.
    onSuccess: async () => {
      navigate(parent.length === 0 ? catalogPath(catalog) : namespacePath(catalog, parent));
      for (const queryKey of [
        catalogQueryKeys.namespace(catalog, parts),
        catalogQueryKeys.namespaces(catalog, parts),
        catalogQueryKeys.tables(catalog, parts),
        catalogQueryKeys.views(catalog, parts),
        catalogQueryKeys.genericTables(catalog, parts),
      ]) {
        queryClient.removeQueries({ queryKey });
      }
      await queryClient.invalidateQueries({ queryKey: catalogQueryKeys.namespaces(catalog, parent), exact: true });
    },
  });

  const queries = [namespace, children, tables, views, genericTables];
  if (queries.some((query) => query.isPending)) return <PanelSkeleton label="Loading namespace" />;
  // Only the namespace itself failing replaces the page; a failed list shows in its section.
  if (!namespace.isSuccess) {
    return (
      <Alert variant="destructive">
        <AlertDescription>Could not load namespace: {errorMessage(namespace.error)}</AlertDescription>
      </Alert>
    );
  }

  const childErrors = children.isError ? [`Could not load namespaces: ${errorMessage(children.error)}`] : [];
  const objectErrors = (
    [
      ["tables", tables],
      ["views", views],
      ["generic tables", genericTables],
    ] as const
  ).flatMap(([label, query]) =>
    query.isError ? [`Could not load ${label}: ${errorMessage(query.error)}`] : [],
  );

  const objectRows: ObjectRow[] = [
    ...(tables.data ?? []).map((item) => ({ type: "table" as const, name: item.name })),
    ...(views.data ?? []).map((item) => ({ type: "view" as const, name: item.name })),
    ...(genericTables.data ?? []).map((item) => ({ type: "generic table" as const, name: item.name })),
  ].sort((a, b) => a.name.localeCompare(b.name) || a.type.localeCompare(b.type));

  function objectPath(row: ObjectRow): string {
    switch (row.type) {
      case "table":
        return tablePath(catalog, parts, row.name);
      case "view":
        return viewPath(catalog, parts, row.name);
      case "generic table":
        return genericTablePath(catalog, parts, row.name);
    }
  }

  const name = lastPart(parts);
  const pathText = (tail: string[]) => [catalog, ...tail].join(" / ");
  const linkClass = "font-mono text-[13px] font-medium underline-offset-4 hover:underline";

  return (
    <>
      <ResourceListPage
        title={name}
        breadcrumbs={breadcrumbs(catalog, parts)}
        actions={
          <ActionsMenu
            items={[
              { label: "Edit properties", onSelect: () => setDialog("edit") },
              {
                label: "Delete",
                onSelect: () => {
                  removeSelf.reset();
                  setDialog("delete");
                },
              },
            ]}
          />
        }
        listTitle="Namespaces"
        columns={[
          {
            header: "Name",
            cell: (row) => (
              <Link to={namespacePath(catalog, row.namespace)} className={linkClass}>
                {lastPart(row.namespace)}
              </Link>
            ),
          },
        ]}
        rows={children.data ?? []}
        rowKey={(row) => row.namespace.join("\u001f")}
        emptyText="No namespaces inside this one."
        errors={childErrors}
        newLabel="New namespace"
        renderForm={({ onClose }) => <CreateNamespaceDialog catalog={catalog} parent={parts} onClose={onClose} />}
        objectKind="namespace"
        objectName={(row) => lastPart(row.namespace)}
        fullPath={(row) => pathText(row.namespace)}
        onDelete={async (row) => {
          await removeChild.mutateAsync(row);
        }}
      >
        <ResourceSection
          title="Tables and views"
          columns={[
            {
              header: "Name",
              cell: (row) => (
                <Link to={objectPath(row)} className={linkClass}>
                  {row.name}
                </Link>
              ),
            },
            { header: "Type", cell: (row) => TYPE_LABEL[row.type] },
          ]}
          rows={objectRows}
          rowKey={(row) => `${row.type}:${row.name}`}
          emptyText="No tables or views."
          errors={objectErrors}
          newLabel="New table or view"
          renderForm={({ onClose }) => (
            <NewNamespaceObjectDialog catalog={catalog} namespace={parts} onClose={onClose} />
          )}
          objectKind={(row) => row.type}
          objectName={(row) => row.name}
          fullPath={(row) => pathText([...parts, row.name])}
          onDelete={async (row) => {
            await removeObject.mutateAsync(row);
          }}
        />
        <PropertiesPanel properties={namespace.data.properties} />
      </ResourceListPage>
      {dialog === "edit" && (
        <EditNamespacePropertiesDialog namespace={namespace.data} onClose={() => setDialog(null)} />
      )}
      {dialog === "delete" && (
        <ConfirmDeleteDialog
          open
          onOpenChange={(next) => !next && setDialog(null)}
          objectKind="namespace"
          objectName={name}
          fullPath={pathText(parts)}
          isPending={removeSelf.isPending}
          error={removeSelf.error}
          onConfirm={() => removeSelf.mutate()}
        />
      )}
    </>
  );
}
