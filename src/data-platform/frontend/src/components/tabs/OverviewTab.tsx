import { Panel, TextLink } from "@retail-lakehouse/design-system";
import type { ReactNode } from "react";
import { Link } from "react-router";
import {
  useGetTableDiscoveryPolicyVersion,
  useListTableDiscoveryPolicies,
} from "@/api/generated/discovery-policies/discovery-policies";
import type { CatalogTableApiResponse, TableApiResponse } from "@/api/generated/model";
import { EffectivePoliciesPanel } from "@/components/EffectivePoliciesPanel";
import { MaintenanceGate } from "@/components/MaintenanceGate";
import { TablePrioritySelect } from "@/components/TablePrioritySelect";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { TableMetricsDashboard } from "@/components/TableMetricsDashboard";
import { formatRelativeTime } from "@/format";
import { discoveryPolicyVersionPath } from "@/lib/discoveryPolicyPaths";
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

// What decided a managed table: the discovery policy and version, linked to that version's page, and
// the deciding rule's position in that version, or that no rule matched. The policy is found by id in
// the list; one deleted since shows its id only, with no link and no rule.
function DecidedBy({ table }: { table: TableApiResponse }) {
  const policies = useListTableDiscoveryPolicies();
  const policy = policies.data?.policies.find((p) => p.id === table.matched_policy_id);
  const ruleId = table.matched_rule_id;
  const version = useGetTableDiscoveryPolicyVersion(policy?.name ?? "", table.matched_policy_version, {
    query: { enabled: policy !== undefined && ruleId !== null },
  });
  if (policies.data === undefined) return null;
  if (policy === undefined) {
    return (
      <>
        {" · discovery policy "}
        <span className="font-mono">{table.matched_policy_id}</span>
        {` v${table.matched_policy_version}`}
      </>
    );
  }
  const position = ruleId === null ? -1 : (version.data?.rules.findIndex((rule) => rule.id === ruleId) ?? -1);
  return (
    <>
      {" · discovery policy "}
      <TextLink asChild inline>
        <Link to={discoveryPolicyVersionPath(policy.name, table.matched_policy_version)}>
          {`${policy.name} v${table.matched_policy_version}`}
        </Link>
      </TextLink>
      {ruleId === null && " · no rule matched"}
      {position >= 0 && (
        <>
          {" · rule "}
          <span className="tabular-nums">{position + 1}</span>
        </>
      )}
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
  return (
    <div className="grid grid-cols-1 gap-4">
      {managed !== null && <TableMetricsDashboard tableUuid={managed.uuid} />}
      <Panel title="Table" actions={
          <span className="type-body-small text-on-surface-variant">
            <span>{MARKER[maintenance.kind]}</span>
            {/* What decided the table is asked for only when maintenance manages it. */}
            {managed !== null && <DecidedBy table={managed} />}
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
        <PanelSkeleton label="Loading policies…" />
      ) : (
        <EffectivePoliciesPanel
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
