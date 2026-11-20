import { Panel, TextLink } from "@retail-lakehouse/design-system";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { useGetTableDiscoveryRules } from "@/api/generated/discovery-rules/discovery-rules";
import type { CatalogTableApiResponse, TableApiResponse } from "@/api/generated/model";
import { ApplicablePolicyPanel } from "@/components/ApplicablePolicyPanel";
import { MaintenanceGate } from "@/components/MaintenanceGate";
import { TablePrioritySelect } from "@/components/TablePrioritySelect";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { TableMetricsDashboard } from "@/components/TableMetricsDashboard";
import { formatRelativeTime } from "@/format";
import type { TableMaintenanceState } from "@/lib/tableMaintenanceState";

interface Props {
  table: CatalogTableApiResponse;
  maintenance: TableMaintenanceState;
  // Maintenance's record of the table, as the page read it; the policy waits for its answer.
  record: { data: TableApiResponse | undefined; isPending: boolean };
}

const MARKER: Record<TableMaintenanceState["kind"], string> = {
  loading: "Maintenance: checking…",
  failed: "Maintenance: unknown",
  unmanaged: "Maintenance: not managed",
  managed: "Maintenance: managed",
};

function Fact({ label, children, mono }: { label: string; children: ReactNode; mono?: boolean }) {
  return (
    <>
      <dt className="text-on-surface-variant">{label}</dt>
      <dd className={mono === true ? "type-code break-all" : "tabular-nums"}>{children}</dd>
    </>
  );
}

// A managed table's metrics first; then what the catalog holds, plus whether maintenance manages the
// table (the header and the cards carry its rows, files and size); then the policy that applies,
// for every table: one maintenance has a record of is read by that record's uuid, any other by its
// name in the catalog, so a policy can be attached before maintenance manages it. When maintenance
// does not manage the table, the shared empty state says why; while maintenance's answer is pending
// the policy's skeleton and the panel marker are the only loading signs.
export function OverviewTab({ table, maintenance, record }: Props) {
  const managed = maintenance.kind === "managed" ? maintenance.table : null;
  // The rule that selected the table is asked for only when maintenance manages it.
  const rules = useGetTableDiscoveryRules({ query: { enabled: managed !== null } });
  const rule = managed === null ? undefined : rules.data?.rules.find((r) => r.id === managed.matched_rule_id);
  return (
    <div className="grid grid-cols-1 gap-4">
      {managed !== null && <TableMetricsDashboard tableUuid={managed.uuid} />}
      <Panel title="Table" actions={
          <span className="type-body-small text-on-surface-variant">
            <span>{MARKER[maintenance.kind]}</span>
            {rule !== undefined && (
              <>
                {" · rule "}
                <TextLink asChild inline className="tabular-nums">
                  <Link to="/discovery-rules">{`Priority ${rule.priority}`}</Link>
                </TextLink>
              </>
            )}
          </span>
        }
      >
        <dl className="grid grid-cols-1 gap-x-4 gap-y-1 sm:grid-cols-[10rem_1fr] sm:gap-y-2">
          <Fact label="Format version">{table.format_version}</Fact>
          <Fact label="Location" mono>
            {table.location}
          </Fact>
          <Fact label="UUID" mono>
            {table.uuid}
          </Fact>
          <Fact label="Current snapshot" mono>
            {table.current_snapshot_id ?? "—"}
          </Fact>
          <Fact label="Last updated">{formatRelativeTime(new Date(table.last_updated_ms).toISOString())}</Fact>
          {record.data !== undefined && (
            <Fact label="Priority">
              <TablePrioritySelect table={record.data} />
            </Fact>
          )}
        </dl>
      </Panel>
      {record.isPending ? (
        <PanelSkeleton label="Loading policy…" />
      ) : (
        <ApplicablePolicyPanel
          scope={{
            type: "table",
            catalog: table.catalog,
            namespace: table.namespace,
            table: table.name,
            tableUuid: record.data?.uuid ?? table.uuid,
            recorded: record.data !== undefined,
          }}
        />
      )}
      {maintenance.kind !== "loading" && <MaintenanceGate state={maintenance}>{() => null}</MaintenanceGate>}
    </div>
  );
}
