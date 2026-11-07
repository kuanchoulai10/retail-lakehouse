import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router";
import { catalogQueryKeys } from "@/api/catalogQueryKeys";
import type { CatalogApiResponse } from "@/api/catalogTypes";
import { apiGet, apiSend } from "@/api/client";
import { CreateCatalogDialog } from "@/components/forms/CreateCatalogDialog";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { ResourceListPage } from "@/components/ResourceListPage";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { errorMessage } from "@/format";
import { catalogApiPath, catalogPath, catalogsApiPath } from "@/lib/catalogPaths";

export function CatalogsPage() {
  const queryClient = useQueryClient();
  const catalogs = useQuery({
    queryKey: catalogQueryKeys.catalogs(),
    queryFn: () => apiGet<CatalogApiResponse[]>(catalogsApiPath()),
  });
  const remove = useMutation({
    mutationFn: (catalog: CatalogApiResponse) => apiSend("DELETE", catalogApiPath(catalog.name)),
    onSuccess: async (_result, catalog) => {
      queryClient.removeQueries({ queryKey: catalogQueryKeys.catalog(catalog.name) });
      await queryClient.invalidateQueries({ queryKey: catalogQueryKeys.catalogs() });
    },
  });

  if (catalogs.isPending) return <PanelSkeleton label="Loading catalogs" />;
  if (catalogs.isError) {
    return (
      <Alert variant="destructive">
        <AlertDescription>Could not load catalogs: {errorMessage(catalogs.error)}</AlertDescription>
      </Alert>
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
            <Link to={catalogPath(row.name)} className="font-medium underline-offset-4 hover:underline">
              {row.name}
            </Link>
          ),
        },
        { header: "Type", cell: (row) => row.type },
        { header: "Storage", cell: (row) => row.storage_config.storage_type },
        {
          header: "Default base location",
          cell: (row) => <span className="break-all font-mono text-[13px]">{row.default_base_location}</span>,
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
