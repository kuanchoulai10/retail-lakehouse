import { Banner, TabItem, TabList, TabPanel, Tabs } from "@retail-lakehouse/design-system";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type MouseEvent } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { ApiError } from "@/api/apiError";
import type { CatalogTableApiResponse, TableApiResponse } from "@/api/generated/model";
import { useGetTableApplicableMaintenancePolicy } from "@/api/generated/maintenance-policies/maintenance-policies";
import { useListCoveredCatalogs } from "@/api/generated/discovery-rules/discovery-rules";
import {
  deleteTable,
  getGetCatalogTableQueryKey,
  getListCatalogTablesQueryKey,
  useGetCatalogTable,
  useGetTable,
} from "@/api/generated/tables/tables";
import { ApplicablePolicyPanel } from "@/components/ApplicablePolicyPanel";
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
import { ReconciliationsTab } from "@/components/tabs/ReconciliationsTab";
import { SchemaTab } from "@/components/tabs/SchemaTab";
import { errorMessage } from "@/format";
import { apiNamespace, namespaceFromParam, namespacePath, tablePath } from "@/lib/catalogPaths";
import { tableMaintenanceState, type TableMaintenanceState } from "@/lib/tableMaintenanceState";
import { useLeavingPage } from "@/lib/useLeavingPage";

// The same tabs on every Iceberg table, managed or not (spec anti-goal).
const TABS = [
  { key: "overview", label: "Overview" },
  { key: "schema", label: "Schema" },
  { key: "commits", label: "Commits" },
  { key: "maintenance", label: "Maintenance" },
  { key: "reconciliations", label: "Reconciliations" },
  { key: "policy", label: "Policy" },
  { key: "properties", label: "Properties" },
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

// The policy is read by the table's uuid, which only maintenance's record of the table answers.
function PolicyTab({ table, tableUuid }: { table: CatalogTableApiResponse; tableUuid: string }) {
  return (
    <ApplicablePolicyPanel
      scope={{ type: "table", catalog: table.catalog, namespace: table.namespace, table: table.name, tableUuid }}
    />
  );
}

function tabBody(
  tab: TabKey,
  table: CatalogTableApiResponse,
  maintenance: TableMaintenanceState,
  record: TableApiResponse | undefined,
) {
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
    case "reconciliations":
      return (
        <MaintenanceGate state={maintenance}>{(managed) => <ReconciliationsTab tableUuid={managed.uuid} />}</MaintenanceGate>
      );
    case "policy":
      // Every table maintenance has a record of has a policy, managed or not; the rest say why not.
      return record === undefined ? (
        <MaintenanceGate state={maintenance}>{(managed) => <PolicyTab table={table} tableUuid={managed.uuid} />}</MaintenanceGate>
      ) : (
        <PolicyTab table={table} tableUuid={record.uuid} />
      );
  }
}

// One page for every Iceberg table, joining two contexts by the table uuid only: the catalog
// table (Polaris facts) and maintenance's table (commits, runs, reconciliations). Keyed by the
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
  const recordUuid = maintenanceTable.data?.uuid;
  // The Policy tab's query, so the header's dry-run badge follows an attach or detach there.
  const policy = useGetTableApplicableMaintenancePolicy(recordUuid ?? "", {
    query: { enabled: recordUuid !== undefined && !leaving },
  });

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
        policy={policy.data ?? null}
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
            {t.key === tab ? <div className="type-body-medium">{tabBody(tab, table.data, maintenance, maintenanceTable.data)}</div> : null}
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
