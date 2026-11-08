import {
  Banner,
  createDataTableColumnHelper,
  DataTable,
  Divider,
  Panel,
} from "@retail-lakehouse/design-system";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/api/client";
import type { JsonObject, TableMaintenancePresetApiResponse } from "@/api/types";
import { PageHeader } from "@/components/PageHeader";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { errorMessage, formatBytes, formatSeconds, formatTimestamp } from "@/format";

const RECONCILE_INTERVAL = "reconcile_interval_seconds";

function isObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function formatSetting(key: string, value: unknown): string {
  if (value === null || value === undefined) return "Default";
  if (typeof value === "number" && key.endsWith("_seconds")) return formatSeconds(value);
  if (typeof value === "number" && key.endsWith("_bytes")) return formatBytes(value);
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

interface OperationRow {
  name: string;
  settings: JsonObject;
}

const operationColumn = createDataTableColumnHelper<OperationRow>();

function Parameters({ settings }: { settings: JsonObject }) {
  const entries = Object.entries(settings)
    .filter(([key]) => key !== "enabled")
    .sort(([a], [b]) => a.localeCompare(b));
  return (
    <dl className="type-code grid grid-cols-[minmax(0,14rem)_1fr] gap-x-4 gap-y-1">
      {entries.map(([key, value]) => (
        <div key={key} className="contents">
          <dt className="text-on-surface-variant">{key}</dt>
          <dd className="tabular-nums">{formatSetting(key, value)}</dd>
        </div>
      ))}
    </dl>
  );
}

const operationColumns = operationColumn.columns([
  operationColumn.accessor("name", {
    header: "Operation",
    enableSorting: false,
    cell: (info) => <span className="type-code">{info.getValue()}</span>,
  }),
  operationColumn.accessor((row) => (row.settings.enabled === false ? "Disabled" : "Enabled"), {
    id: "state",
    header: "State",
    enableSorting: false,
    cell: (info) => <span className="text-on-surface-variant">{info.getValue()}</span>,
  }),
  operationColumn.display({
    id: "parameters",
    header: "Parameters",
    cell: (info) => <Parameters settings={info.row.original.settings} />,
  }),
]);

function PresetPanel({ preset }: { preset: TableMaintenancePresetApiResponse }) {
  const operations = Object.entries(preset.settings)
    .filter((entry): entry is [string, JsonObject] => isObject(entry[1]))
    .sort(([a], [b]) => a.localeCompare(b));
  const scalars = Object.entries(preset.settings).filter(([, value]) => !isObject(value));
  return (
    <div id={`preset-${preset.id}`} className="scroll-mt-6">
      <Panel title={preset.name}>
        <dl className="grid grid-cols-1 gap-x-4 gap-y-1 sm:grid-cols-[10rem_1fr] sm:gap-y-2">
          <dt className="text-on-surface-variant">ID</dt>
          <dd className="type-code break-all">{preset.id}</dd>
          {scalars.map(([key, value]) => (
            <div key={key} className="contents">
              <dt className="text-on-surface-variant">
                {key === RECONCILE_INTERVAL ? "Reconcile interval" : <span className="font-mono">{key}</span>}
              </dt>
              <dd className="type-code tabular-nums">{formatSetting(key, value)}</dd>
            </div>
          ))}
          <dt className="text-on-surface-variant">Updated</dt>
          <dd className="tabular-nums">
            <time dateTime={preset.updated_at}>{formatTimestamp(preset.updated_at)}</time>
          </dd>
        </dl>
        <Divider className="my-4" />
        <DataTable
          caption={`${preset.name} operations`}
          columns={operationColumns}
          data={operations.map(([name, settings]) => ({ name, settings }))}
          getRowId={(row) => row.name}
          emptyState="No operations."
        />
      </Panel>
    </div>
  );
}

export function PresetsPage() {
  const presets = useQuery({
    queryKey: ["table-maintenance-presets"],
    queryFn: () => apiGet<TableMaintenancePresetApiResponse[]>("/v1/table-maintenance-presets"),
  });

  return (
    <section>
      <PageHeader title="Presets">
        <span>Maintenance settings that discovery rules give to the tables they include.</span>
      </PageHeader>
      {presets.isError && (
        <Banner type="negative" title={`Could not load presets: ${errorMessage(presets.error)}`} />
      )}
      {presets.isPending && <PanelSkeleton label="Loading presets" />}
      {presets.isSuccess && (
        <div className="flex flex-col gap-6">
          {[...presets.data]
            .sort((a, b) => a.name.localeCompare(b.name))
            .map((preset) => (
              <PresetPanel key={preset.id} preset={preset} />
            ))}
          {presets.data.length === 0 && <p className="text-on-surface-variant">No presets.</p>}
        </div>
      )}
    </section>
  );
}
