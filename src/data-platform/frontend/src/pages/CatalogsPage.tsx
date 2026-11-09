import { Banner, TextLink } from "@retail-lakehouse/design-system";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router";
import {
  deleteCatalog,
  getGetCatalogQueryKey,
  getListCatalogsQueryKey,
  useListCatalogs,
} from "@/api/generated/catalogs/catalogs";
import type { CatalogApiResponse } from "@/api/generated/model";
import { CreateCatalogDialog } from "@/components/forms/CreateCatalogDialog";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { ResourceListPage } from "@/components/ResourceListPage";
import { errorMessage } from "@/format";
import { catalogPath } from "@/lib/catalogPaths";

export function CatalogsPage() {
  const queryClient = useQueryClient();
  const catalogs = useListCatalogs();
  const remove = useMutation({
    mutationFn: (catalog: CatalogApiResponse) => deleteCatalog(catalog.name),
    onSuccess: async (_result, catalog) => {
      queryClient.removeQueries({ queryKey: getGetCatalogQueryKey(catalog.name) });
      await queryClient.invalidateQueries({ queryKey: getListCatalogsQueryKey() });
    },
  });

  if (catalogs.isPending) return <PanelSkeleton label="Loading catalogs" />;
  if (catalogs.isError) {
    return (
      <Banner type="negative" title={`Could not load catalogs: ${errorMessage(catalogs.error)}`} />
    );
  }

  const rows = [...catalogs.data].sort((a, b) => a.name.localeCompare(b.name));
  return (
    <ResourceListPage
      title="Catalogs"
      columns={[
        {
          header: "Name",
          cell: (row) => (
            <TextLink asChild className="font-medium">
              <Link to={catalogPath(row.name)}>
                {row.name}
              </Link>
            </TextLink>
          ),
        },
        { header: "Type", cell: (row) => row.type },
        { header: "Storage", cell: (row) => row.storage_config.storage_type },
        {
          header: "Default base location",
          cell: (row) => <span className="type-code break-all">{row.default_base_location}</span>,
        },
      ]}
      rows={rows}
      rowKey={(row) => row.name}
      emptyText="No catalogs."
      newLabel="New catalog"
      renderForm={({ onClose }) => <CreateCatalogDialog onClose={onClose} />}
      objectKind="catalog"
      objectName={(row) => row.name}
      fullPath={(row) => row.name}
      onDelete={async (row) => {
        await remove.mutateAsync(row);
      }}
    />
  );
}
