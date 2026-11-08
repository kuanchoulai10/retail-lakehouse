import { Banner } from "@retail-lakehouse/design-system";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { catalogQueryKeys } from "@/api/catalogQueryKeys";
import type { CatalogApiResponse, NamespaceSummaryApiResponse } from "@/api/catalogTypes";
import { apiGet, apiSend } from "@/api/client";
import { CatalogDetails } from "@/components/CatalogDetails";
import { ConfirmDeleteDialog } from "@/components/ConfirmDeleteDialog";
import { CreateNamespaceDialog } from "@/components/forms/CreateNamespaceDialog";
import { EditCatalogDialog } from "@/components/forms/EditCatalogDialog";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { PropertiesPanel } from "@/components/PropertiesPanel";
import { ResourceListPage } from "@/components/ResourceListPage";
import { errorMessage } from "@/format";
import {
  catalogApiPath,
  catalogsPath,
  namespaceApiPath,
  namespacePath,
  namespacesApiPath,
} from "@/lib/catalogPaths";
import { useLeavingPage } from "@/lib/useLeavingPage";

type Dialog = "edit" | "delete" | null;

// Keyed by the catalog, so leaving after a delete always unmounts it (see useLeavingPage).
export function CatalogPage() {
  const { catalog: name = "" } = useParams();
  return <CatalogDetailsPage key={name} name={name} />;
}

function CatalogDetailsPage({ name }: { name: string }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [dialog, setDialog] = useState<Dialog>(null);
  const { leaving, leave } = useLeavingPage([catalogQueryKeys.catalog(name), catalogQueryKeys.namespaceLists(name)]);

  const catalog = useQuery({
    queryKey: catalogQueryKeys.catalog(name),
    queryFn: () => apiGet<CatalogApiResponse>(catalogApiPath(name)),
    enabled: !leaving,
  });
  const namespaces = useQuery({
    queryKey: catalogQueryKeys.namespaces(name, []),
    queryFn: () => apiGet<NamespaceSummaryApiResponse[]>(namespacesApiPath(name, [])),
    enabled: !leaving,
  });

  const removeNamespace = useMutation({
    mutationFn: (row: NamespaceSummaryApiResponse) => apiSend("DELETE", namespaceApiPath(name, row.namespace)),
    onSuccess: async (_result, row) => {
      queryClient.removeQueries({ queryKey: catalogQueryKeys.namespace(name, row.namespace) });
      await queryClient.invalidateQueries({ queryKey: catalogQueryKeys.namespaceLists(name) });
    },
  });
  const removeCatalog = useMutation({
    mutationFn: () => apiSend("DELETE", catalogApiPath(name)),
    // Stop the catalog's queries before leaving, so nothing refetches the catalog that is
    // gone; they are dropped when the page unmounts (see useLeavingPage).
    onSuccess: async () => {
      leave();
      navigate(catalogsPath());
      await queryClient.invalidateQueries({ queryKey: catalogQueryKeys.catalogs() });
    },
  });

  if (catalog.isPending || namespaces.isPending) return <PanelSkeleton label="Loading catalog" />;
  if (catalog.isError || namespaces.isError) {
    const what = catalog.isError ? "catalog" : "namespaces";
    return (
      <Banner type="negative" title={`Could not load ${what}: ${errorMessage(catalog.error ?? namespaces.error)}`} />
    );
  }

  const rows = [...namespaces.data].sort((a, b) => a.namespace.join("\u001f").localeCompare(b.namespace.join("\u001f")));
  const last = (row: NamespaceSummaryApiResponse) => row.namespace[row.namespace.length - 1] ?? "";

  return (
    <>
      <ResourceListPage
        title={name}
        breadcrumbs={[{ label: "Catalogs", to: catalogsPath() }, { label: name }]}
        menuItems={[
          { label: "Edit", onSelect: () => setDialog("edit") },
          {
            label: "Delete",
            destructive: true,
            onSelect: () => {
              removeCatalog.reset();
              setDialog("delete");
            },
          },
        ]}
        listTitle="Namespaces"
        columns={[
          {
            header: "Name",
            cell: (row) => (
              <Link
                to={namespacePath(name, row.namespace)}
                className="font-mono font-medium underline-offset-4 hover:underline"
              >
                {last(row)}
              </Link>
            ),
          },
        ]}
        rows={rows}
        rowKey={(row) => row.namespace.join("\u001f")}
        emptyText="No namespaces."
        newLabel="New namespace"
        renderForm={({ onClose }) => <CreateNamespaceDialog catalog={name} parent={[]} onClose={onClose} />}
        objectKind="namespace"
        objectName={last}
        fullPath={(row) => [name, ...row.namespace].join(" / ")}
        onDelete={async (row) => {
          await removeNamespace.mutateAsync(row);
        }}
      >
        <CatalogDetails catalog={catalog.data} />
        <PropertiesPanel properties={catalog.data.properties} />
      </ResourceListPage>
      {dialog === "edit" && <EditCatalogDialog catalog={catalog.data} onClose={() => setDialog(null)} />}
      {dialog === "delete" && (
        <ConfirmDeleteDialog
          open
          onOpenChange={(next) => !next && setDialog(null)}
          objectKind="catalog"
          objectName={name}
          fullPath={name}
          isPending={removeCatalog.isPending}
          error={removeCatalog.error}
          onConfirm={() => removeCatalog.mutate()}
        />
      )}
    </>
  );
}
