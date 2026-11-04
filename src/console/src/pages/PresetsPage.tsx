import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/api/client";
import type { JsonObject, TableMaintenancePresetApiResponse } from "@/api/types";
import { PageHeader } from "@/components/PageHeader";
import { Panel } from "@/components/Panel";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
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

function OperationRow({ name, settings }: { name: string; settings: JsonObject }) {
  const { enabled, ...parameters } = settings;
  const entries = Object.entries(parameters).sort(([a], [b]) => a.localeCompare(b));
  return (
    <TableRow>
      <TableCell className="align-top font-mono text-[13px]">{name}</TableCell>
      <TableCell className="align-top text-muted-foreground">
        {enabled === false ? "Disabled" : "Enabled"}
      </TableCell>
      <TableCell>
        <dl className="grid grid-cols-[minmax(0,14rem)_1fr] gap-x-4 gap-y-1">
          {entries.map(([key, value]) => (
            <div key={key} className="contents">
              <dt className="font-mono text-[13px] text-muted-foreground">{key}</dt>
              <dd className="font-mono text-[13px] tabular-nums">{formatSetting(key, value)}</dd>
            </div>
          ))}
        </dl>
      </TableCell>
    </TableRow>
  );
}

function PresetPanel({ preset }: { preset: TableMaintenancePresetApiResponse }) {
  const operations = Object.entries(preset.settings)
    .filter((entry): entry is [string, JsonObject] => isObject(entry[1]))
    .sort(([a], [b]) => a.localeCompare(b));
  const scalars = Object.entries(preset.settings).filter(([, value]) => !isObject(value));
  return (
    <div id={`preset-${preset.id}`} className="scroll-mt-6">
      <Panel title={preset.name}>
        <dl className="grid grid-cols-[10rem_1fr] gap-x-4 gap-y-2 border-b border-border px-4 py-3">
          <dt className="text-muted-foreground">ID</dt>
          <dd className="break-all font-mono text-[13px]">{preset.id}</dd>
          {scalars.map(([key, value]) => (
            <div key={key} className="contents">
              <dt className="text-muted-foreground">
                {key === RECONCILE_INTERVAL ? "Reconcile interval" : <span className="font-mono text-[13px]">{key}</span>}
              </dt>
              <dd className="font-mono text-[13px] tabular-nums">{formatSetting(key, value)}</dd>
            </div>
          ))}
          <dt className="text-muted-foreground">Updated</dt>
          <dd className="tabular-nums">
            <time dateTime={preset.updated_at}>{formatTimestamp(preset.updated_at)}</time>
          </dd>
        </dl>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Operation</TableHead>
              <TableHead>State</TableHead>
              <TableHead>Parameters</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {operations.map(([name, settings]) => (
              <OperationRow key={name} name={name} settings={settings} />
            ))}
            {operations.length === 0 && (
              <TableRow>
                <TableCell colSpan={3} className="text-center text-muted-foreground">
                  No operations.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
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
        <Alert variant="destructive">
          <AlertDescription>Could not load presets: {errorMessage(presets.error)}</AlertDescription>
        </Alert>
      )}
      {presets.isPending && <PanelSkeleton label="Loading presets" />}
      {presets.isSuccess && (
        <div className="flex flex-col gap-6">
          {[...presets.data]
            .sort((a, b) => a.name.localeCompare(b.name))
            .map((preset) => (
              <PresetPanel key={preset.id} preset={preset} />
            ))}
          {presets.data.length === 0 && <p className="text-muted-foreground">No presets.</p>}
        </div>
      )}
    </section>
  );
}
