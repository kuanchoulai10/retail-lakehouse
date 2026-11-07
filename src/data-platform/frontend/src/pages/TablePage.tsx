import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type MouseEvent } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { catalogQueryKeys } from "@/api/catalogQueryKeys";
import type { CatalogTableApiResponse, CoveredCatalogsApiResponse } from "@/api/catalogTypes";
import { ApiError, apiGet, apiSend } from "@/api/client";
import type { TableApiResponse } from "@/api/types";
import { ActionsMenu } from "@/components/ActionsMenu";
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
import { SnapshotsTab } from "@/components/tabs/SnapshotsTab";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { errorMessage } from "@/format";
import { namespaceFromParam, namespacePath, tableApiPath, tablePath } from "@/lib/catalogPaths";
import { tableMaintenanceState, type TableMaintenanceState } from "@/lib/tableMaintenanceState";
import { useLeavingPage } from "@/lib/useLeavingPage";

// The same seven tabs on every Iceberg table, managed or not (spec anti-goal).
const TABS = [
  { key: "overview", label: "Overview" },
  { key: "schema", label: "Schema" },
  { key: "snapshots", label: "Snapshots" },
  { key: "commits", label: "Commits" },
  { key: "maintenance", label: "Maintenance" },
  { key: "properties", label: "Properties" },
  { key: "settings", label: "Settings" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

type Dialog = "rename" | "edit" | "delete" | null;

const COVERED_CATALOGS_KEY = ["covered-catalogs"] as const;

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
    case "snapshots":
      return <SnapshotsTab table={table} />;
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
  const { leaving, leave } = useLeavingPage([catalogQueryKeys.table(catalog, parts, name)]);

  const table = useQuery({
    queryKey: catalogQueryKeys.table(catalog, parts, name),
    queryFn: () => apiGet<CatalogTableApiResponse>(tableApiPath(catalog, parts, name)),
    enabled: !leaving,
  });
  const covered = useQuery({
    queryKey: COVERED_CATALOGS_KEY,
    queryFn: async () =>
      (await apiGet<CoveredCatalogsApiResponse>("/v1/table-discovery-settings/catalogs")).catalogs,
  });
  const uuid = table.data?.uuid;
  const maintenanceTable = useQuery({
    // The key the maintenance tabs and invalidateTableState share.
    queryKey: ["table", uuid ?? ""],
    queryFn: () => apiGet<TableApiResponse>(`/v1/tables/${uuid ?? ""}`),
    enabled: uuid !== undefined && !leaving,
  });

  const remove = useMutation({
    mutationFn: () => apiSend("DELETE", tableApiPath(catalog, parts, name)),
    // Stop the table's queries before leaving, so nothing refetches what is gone (see
    // useLeavingPage); only the namespace's table listing is refetched.
    onSuccess: async () => {
      leave();
      navigate(namespacePath(catalog, parts));
      await queryClient.invalidateQueries({ queryKey: catalogQueryKeys.tables(catalog, parts), exact: true });
    },
  });

  if (table.isPending) return <PanelSkeleton label="Loading table…" />;
  if (table.isError) {
    if (isNotFound(table.error)) {
      return <CatalogObjectNotFound objectKind="table" catalog={catalog} namespace={parts} name={name} />;
    }
    return (
      <Alert variant="destructive">
        <AlertDescription>Could not load table: {errorMessage(table.error)}</AlertDescription>
      </Alert>
    );
  }

  const maintenance = tableMaintenanceState(catalog, covered, maintenanceTable);
  const menu = (
    <ActionsMenu
      items={[
        { label: "Rename", onSelect: () => setDialog("rename") },
        { label: "Edit properties", onSelect: () => setDialog("edit") },
        {
          label: "Delete",
          onSelect: () => {
            remove.reset();
            setDialog("delete");
          },
        },
      ]}
    />
  );

  return (
    <section>
      <TableHeader
        table={table.data}
        managed={maintenance.kind === "managed" ? maintenance.table : null}
        menu={menu}
      />
      <Tabs value={tab} onValueChange={(next) => navigate(tablePath(catalog, parts, name, next))}>
        <TabsList
          variant="line"
          aria-label="Table sections"
          className="mb-4 max-w-full justify-start overflow-x-auto border-b border-border"
        >
          {TABS.map((t) => (
            <TabsTrigger key={t.key} value={t.key} asChild onMouseDown={keepPageOnModifiedClick}>
              <Link to={tablePath(catalog, parts, name, t.key)}>{t.label}</Link>
            </TabsTrigger>
          ))}
        </TabsList>
        {TABS.map((t) => (
          <TabsContent key={t.key} value={t.key} forceMount>
            {t.key === tab ? tabBody(tab, table.data, maintenance) : null}
          </TabsContent>
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
