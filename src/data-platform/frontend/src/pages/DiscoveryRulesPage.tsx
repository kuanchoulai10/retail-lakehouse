import {
  Banner,
  createDataTableColumnHelper,
  DataTable,
  Skeleton,
  TextLink,
} from "@retail-lakehouse/design-system";
import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { Link } from "react-router";
import { apiGet } from "@/api/client";
import type {
  TableDiscoveryRuleApiResponse,
  TableDiscoverySettingsApiResponse,
  TableMaintenancePresetApiResponse,
} from "@/api/types";
import { PageHeader } from "@/components/PageHeader";
import { errorMessage, formatTimestamp } from "@/format";

const SKELETON_ROWS = 3;

const column = createDataTableColumnHelper<TableDiscoveryRuleApiResponse>();

function capitalise(word: string): string {
  return word.charAt(0).toUpperCase() + word.slice(1);
}

function pattern(rule: TableDiscoveryRuleApiResponse): string {
  return `${rule.catalog_pattern}.${rule.namespace_pattern}.${rule.table_pattern}`;
}

function byEvaluationOrder(a: TableDiscoveryRuleApiResponse, b: TableDiscoveryRuleApiResponse): number {
  return a.priority - b.priority || a.id.localeCompare(b.id);
}

function rulesColumns(presetNames: Map<string, string>) {
  return column.columns([
    column.accessor("priority", {
      header: "Priority",
      enableSorting: false,
      cell: (info) => <span className="tabular-nums">{info.getValue()}</span>,
    }),
    column.accessor("effect", { header: "Effect", enableSorting: false, cell: (info) => capitalise(info.getValue()) }),
    column.accessor((rule) => pattern(rule), {
      id: "pattern",
      header: "Pattern",
      enableSorting: false,
      cell: (info) => <span className="type-code whitespace-nowrap">{info.getValue()}</span>,
    }),
    column.accessor("preset_id", {
      header: "Preset",
      enableSorting: false,
      cell: (info) => {
        const presetId = info.getValue();
        if (presetId === null) return <span className="text-on-surface-variant">—</span>;
        return (
          <TextLink asChild className="font-mono">
            <Link to={`/presets#preset-${presetId}`}>
              {presetNames.get(presetId) ?? presetId}
            </Link>
          </TextLink>
        );
      },
    }),
    column.accessor((rule) => (rule.enabled ? "Enabled" : "Disabled"), {
      id: "state",
      header: "State",
      enableSorting: false,
      cell: (info) => <span className="text-on-surface-variant">{info.getValue()}</span>,
    }),
    column.accessor("updated_at", {
      header: "Updated",
      enableSorting: false,
      cell: (info) => (
        <time dateTime={info.getValue()} className="tabular-nums whitespace-nowrap">
          {formatTimestamp(info.getValue())}
        </time>
      ),
    }),
  ]);
}

function LoadingRows() {
  return (
    <div className="grid gap-3 py-1">
      {Array.from({ length: SKELETON_ROWS }, (_, i) => (
        <Skeleton key={i} className="h-4 w-full" />
      ))}
    </div>
  );
}

function DiscoveryState() {
  const settings = useQuery({
    queryKey: ["table-discovery-settings"],
    queryFn: () => apiGet<TableDiscoverySettingsApiResponse>("/v1/table-discovery-settings"),
  });
  if (!settings.isSuccess) return null;
  return <span>{settings.data.enabled ? "Discovery is on" : "Discovery is off"}</span>;
}

export function DiscoveryRulesPage() {
  const rules = useQuery({
    queryKey: ["table-discovery-rules"],
    queryFn: () => apiGet<TableDiscoveryRuleApiResponse[]>("/v1/table-discovery-rules"),
  });
  const presets = useQuery({
    queryKey: ["table-maintenance-presets"],
    queryFn: () => apiGet<TableMaintenancePresetApiResponse[]>("/v1/table-maintenance-presets"),
  });

  const presetNames = useMemo(
    () => new Map((presets.data ?? []).map((preset) => [preset.id, preset.name])),
    [presets.data],
  );
  const ordered = useMemo(() => [...(rules.data ?? [])].sort(byEvaluationOrder), [rules.data]);
  const columns = useMemo(() => rulesColumns(presetNames), [presetNames]);

  return (
    <section>
      <PageHeader title="Discovery rules">
        <DiscoveryState />
        <span>Lowest priority first; the first enabled rule that matches a table decides.</span>
      </PageHeader>
      {rules.isError && (
        <Banner type="negative" title={`Could not load discovery rules: ${errorMessage(rules.error)}`} />
      )}
      {!rules.isError && (
        <div aria-busy={rules.isPending}>
          <DataTable
            caption="Discovery rules in evaluation order"
            columns={columns}
            data={rules.isSuccess ? ordered : []}
            getRowId={(rule) => rule.id}
            emptyState={rules.isPending ? <LoadingRows /> : "No discovery rules."}
          />
        </div>
      )}
    </section>
  );
}
