import { Banner, TabItem, TabList, TabPanel, Tabs } from "@retail-lakehouse/design-system";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type MouseEvent } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { ApiError } from "@/api/apiError";
import type { CatalogTableApiResponse } from "@/api/generated/model";
import { useListCoveredCatalogs } from "@/api/generated/table-discovery-settings/table-discovery-settings";
import {
  deleteTable,
  getGetCatalogTableQueryKey,
  getListCatalogTablesQueryKey,
  useGetCatalogTable,
  useGetTable,
} from "@/api/generated/tables/tables";
import { CatalogObjectNotFound } from "@/components/CatalogObjectNotFound";
import { ConfirmDeleteDialog } from "@/components/ConfirmDeleteDialog";
import { EditTablePropertiesDialog } from "@/components/forms/EditTablePropertiesDialog";
import { RenameTableDialog } from "@/components/forms/RenameTableDialog";
import { MaintenanceGate } from "@/components/MaintenanceGate";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { TableHeader } from "@/components/TableHeader";
import { CommitsTab } from "@/components/tabs/CommitsTab";
import { MaintenanceTab } from "@/components/tabs/MaintenanceTab";
import { OverviewTab } from "@/components/tabs/OverviewTab";
import { PropertiesTab } from "@/components/tabs/PropertiesTab";
import { SchemaTab } from "@/components/tabs/SchemaTab";
import { SettingsTab } from "@/components/tabs/SettingsTab";
import { errorMessage } from "@/format";
import { apiNamespace, namespaceFromParam, namespacePath, tablePath } from "@/lib/catalogPaths";
import { tableMaintenanceState, type TableMaintenanceState } from "@/lib/tableMaintenanceState";
import { useLeavingPage } from "@/lib/useLeavingPage";

// The same six tabs on every Iceberg table, managed or not (spec anti-goal).
const TABS = [
  { key: "overview", label: "Overview" },
  { key: "schema", label: "Schema" },
  { key: "commits", label: "Commits" },
  { key: "maintenance", label: "Maintenance" },
  { key: "properties", label: "Properties" },
  { key: "settings", label: "Settings" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

type Dialog = "rename" | "edit" | "delete" | null;

function tabOf(segment: string | undefined): TabKey {
  return TABS.find((t) => t.key === segment)?.key ?? "overview";
}

function keepPageOnModifiedClick(event: MouseEvent<HTMLElement>) {
  if (event.metaKey || event.shiftKey || event.altKey) event.preventDefault();
}

function isNotFound(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}

function tabBody(tab: TabKey, table: CatalogTableApiResponse, maintenance: TableMaintenanceState) {
  switch (tab) {
    case "overview":
      return <OverviewTab table={table} maintenance={maintenance} />;
    case "schema":
      return <SchemaTab table={table} />;
    case "properties":
      return <PropertiesTab table={table} />;
    case "commits":
      return <MaintenanceGate state={maintenance}>{(managed) => <CommitsTab tableUuid={managed.uuid} />}</MaintenanceGate>;
    case "maintenance":
      return <MaintenanceGate state={maintenance}>{(managed) => <MaintenanceTab tableUuid={managed.uuid} />}</MaintenanceGate>;
    case "settings":
      return <MaintenanceGate state={maintenance}>{(managed) => <SettingsTab tableUuid={managed.uuid} />}</MaintenanceGate>;
  }
}

// One page for every Iceberg table, joining two contexts by the table uuid only: the catalog
// table (Polaris facts) and maintenance's table (commits, runs, settings). Keyed by the
// table's path, so a rename or delete always unmounts it and the next table gets a fresh page.
export function TablePage() {
  const { catalog = "", namespace: param = "", table: name = "", tab } = useParams();
  return <TableView key={JSON.stringify([catalog, param, name])} catalog={catalog} parts={namespaceFromParam(param)} name={name} segment={tab} />;
}

interface TableViewProps {
  catalog: string;
  parts: string[];
  name: string;
  segment: string | undefined;
}

function TableView({ catalog, parts, name, segment }: TableViewProps) {
  const tab = tabOf(segment);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [dialog, setDialog] = useState<Dialog>(null);
  const ns = apiNamespace(parts);
  const { leaving, leave } = useLeavingPage([getGetCatalogTableQueryKey(catalog, ns, name)]);

  const table = useGetCatalogTable(catalog, ns, name, { query: { enabled: !leaving } });
  const covered = useListCoveredCatalogs({ query: { select: (response) => response.catalogs } });
  const uuid = table.data?.uuid;
  // The same query the maintenance tabs use, so invalidateTableState refetches it too.
  const maintenanceTable = useGetTable(uuid ?? "", { query: { enabled: uuid !== undefined && !leaving } });

  const remove = useMutation({
    mutationFn: () => deleteTable(catalog, ns, name),
    // Stop the table's queries before leaving, so nothing refetches what is gone (see
    // useLeavingPage); only the namespace's table listing is refetched.
    onSuccess: async () => {
      leave();
      navigate(namespacePath(catalog, parts));
      await queryClient.invalidateQueries({ queryKey: getListCatalogTablesQueryKey(catalog, ns), exact: true });
    },
  });

  if (table.isPending) return <PanelSkeleton label="Loading table…" />;
  if (table.isError) {
    if (isNotFound(table.error)) {
      return <CatalogObjectNotFound objectKind="table" catalog={catalog} namespace={parts} name={name} />;
    }
    return <Banner type="negative" title={`Could not load table: ${errorMessage(table.error)}`} />;
  }

  const maintenance = tableMaintenanceState(catalog, covered, maintenanceTable);
  const menuItems = [
    { label: "Rename", onSelect: () => setDialog("rename") },
    { label: "Edit properties", onSelect: () => setDialog("edit") },
    {
      label: "Delete",
      destructive: true,
      onSelect: () => {
        remove.reset();
        setDialog("delete");
      },
    },
  ];

  return (
    <section>
      <TableHeader
        table={table.data}
        managed={maintenance.kind === "managed" ? maintenance.table : null}
        menuItems={menuItems}
      />
      <Tabs value={tab} onValueChange={(next) => navigate(tablePath(catalog, parts, name, next))}>
        <TabList aria-label="Table sections">
          {TABS.map((t) => (
            <TabItem key={t.key} value={t.key} asChild onMouseDown={keepPageOnModifiedClick}>
              <Link to={tablePath(catalog, parts, name, t.key)}>{t.label}</Link>
            </TabItem>
          ))}
        </TabList>
        {TABS.map((t) => (
          <TabPanel key={t.key} value={t.key} forceMount className="data-[state=inactive]:hidden">
            {t.key === tab ? <div className="type-body-medium">{tabBody(tab, table.data, maintenance)}</div> : null}
          </TabPanel>
        ))}
      </Tabs>
      {dialog === "rename" && <RenameTableDialog table={table.data} tab={tab} onLeave={leave} onClose={() => setDialog(null)} />}
      {dialog === "edit" && <EditTablePropertiesDialog table={table.data} onClose={() => setDialog(null)} />}
      {dialog === "delete" && (
        <ConfirmDeleteDialog
          open
          onOpenChange={(next) => !next && setDialog(null)}
          objectKind="table"
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
