import { Banner, TextLink } from "@retail-lakehouse/design-system";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import {
  deleteCatalog,
  getGetCatalogQueryKey,
  getListCatalogsQueryKey,
  useGetCatalog,
} from "@/api/generated/catalogs/catalogs";
import type { NamespaceSummaryApiResponse } from "@/api/generated/model";
import {
  deleteNamespace,
  getGetNamespaceQueryKey,
  getListNamespacesQueryKey,
  useListNamespaces,
} from "@/api/generated/namespaces/namespaces";
import { CatalogDetails } from "@/components/CatalogDetails";
import { ConfirmDeleteDialog } from "@/components/ConfirmDeleteDialog";
import { CreateNamespaceDialog } from "@/components/forms/CreateNamespaceDialog";
import { EditCatalogDialog } from "@/components/forms/EditCatalogDialog";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { PropertiesPanel } from "@/components/PropertiesPanel";
import { ResourceListPage } from "@/components/ResourceListPage";
import { errorMessage } from "@/format";
import { apiNamespace, catalogsPath, namespacePath } from "@/lib/catalogPaths";
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
  // The namespace listing key without params is the prefix of every listing in the catalog.
  const { leaving, leave } = useLeavingPage([getGetCatalogQueryKey(name), getListNamespacesQueryKey(name)]);

  const catalog = useGetCatalog(name, { query: { enabled: !leaving } });
  const namespaces = useListNamespaces(name, undefined, { query: { enabled: !leaving } });

  const removeNamespace = useMutation({
    mutationFn: (row: NamespaceSummaryApiResponse) => deleteNamespace(name, apiNamespace(row.namespace)),
    onSuccess: async (_result, row) => {
      queryClient.removeQueries({ queryKey: getGetNamespaceQueryKey(name, apiNamespace(row.namespace)) });
      await queryClient.invalidateQueries({ queryKey: getListNamespacesQueryKey(name) });
    },
  });
  const removeCatalog = useMutation({
    mutationFn: () => deleteCatalog(name),
    // Stop the catalog's queries before leaving, so nothing refetches the catalog that is
    // gone; they are dropped when the page unmounts (see useLeavingPage).
    onSuccess: async () => {
      leave();
      navigate(catalogsPath());
      await queryClient.invalidateQueries({ queryKey: getListCatalogsQueryKey() });
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
              <TextLink asChild className="font-mono font-medium">
                <Link to={namespacePath(name, row.namespace)}>
                  {last(row)}
                </Link>
              </TextLink>
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
