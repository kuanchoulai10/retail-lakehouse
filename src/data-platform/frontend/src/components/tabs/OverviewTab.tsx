import { Panel, TextLink } from "@retail-lakehouse/design-system";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { useGetTableDiscoveryRules } from "@/api/generated/discovery-rules/discovery-rules";
import type { CatalogTableApiResponse } from "@/api/generated/model";
import { MaintenanceGate } from "@/components/MaintenanceGate";
import { formatBytes, formatCount, formatRelativeTime } from "@/format";
import type { TableMaintenanceState } from "@/lib/tableMaintenanceState";

interface Props {
  table: CatalogTableApiResponse;
  maintenance: TableMaintenanceState;
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

// What the catalog holds, plus whether maintenance manages the table; when it does not, the shared
// empty state says why.
export function OverviewTab({ table, maintenance }: Props) {
  const managed = maintenance.kind === "managed" ? maintenance.table : null;
  // The rule that selected the table is asked for only when maintenance manages it.
  const rules = useGetTableDiscoveryRules({ query: { enabled: managed !== null } });
  const rule = managed === null ? undefined : rules.data?.rules.find((r) => r.id === managed.matched_rule_id);
  const { total_records: records, total_data_files: files, total_files_size: size } = table.summary;
  return (
    <div className="grid grid-cols-1 gap-4">
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
          <Fact label="Rows">{formatCount(records)}</Fact>
          <Fact label="Data files">{formatCount(files)}</Fact>
          <Fact label="Size">{size === null ? "—" : formatBytes(size)}</Fact>
          <Fact label="Last updated">{formatRelativeTime(new Date(table.last_updated_ms).toISOString())}</Fact>
        </dl>
      </Panel>
      <MaintenanceGate state={maintenance}>{() => null}</MaintenanceGate>
    </div>
  );
}
