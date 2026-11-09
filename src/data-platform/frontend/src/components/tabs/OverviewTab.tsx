import { Panel } from "@retail-lakehouse/design-system";
import type { ReactNode } from "react";
import type { CatalogTableApiResponse } from "@/api/generated/model";
import { MaintenanceGate } from "@/components/MaintenanceGate";
import { MaintenancePanels } from "@/components/MaintenancePanels";
import { formatBytes, formatCount, formatRelativeTime } from "@/format";
import { currentSnapshot } from "@/lib/currentSnapshot";
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

// Top: what the catalog holds, plus whether maintenance manages the table. Bottom: the
// maintenance panels, or the shared empty state.
export function OverviewTab({ table, maintenance }: Props) {
  const snapshot = currentSnapshot(table);
  const lastCommittedAt = snapshot === undefined ? null : new Date(snapshot.timestamp_ms).toISOString();
  const { total_records: records, total_data_files: files, total_files_size: size } = table.summary;
  return (
    <div className="grid grid-cols-1 gap-4">
      <Panel title="Table" actions={<span className="type-body-small text-on-surface-variant">{MARKER[maintenance.kind]}</span>}>
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
      <MaintenanceGate state={maintenance}>
        {(managed) => <MaintenancePanels tableUuid={managed.uuid} lastCommittedAt={lastCommittedAt} />}
      </MaintenanceGate>
    </div>
  );
}
