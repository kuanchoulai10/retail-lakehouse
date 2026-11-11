import {
  Banner,
  createDataTableColumnHelper,
  DataTable,
  Skeleton,
} from "@retail-lakehouse/design-system";
import { useMemo } from "react";
import type { TableDiscoveryRuleApiResponse } from "@/api/generated/model";
import { useListTableDiscoveryRules } from "@/api/generated/table-discovery-rules/table-discovery-rules";
import { useGetTableDiscoverySettings } from "@/api/generated/table-discovery-settings/table-discovery-settings";
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

function rulesColumns() {
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
  const settings = useGetTableDiscoverySettings();
  if (!settings.isSuccess) return null;
  return <span>{settings.data.enabled ? "Discovery is on" : "Discovery is off"}</span>;
}

export function DiscoveryRulesPage() {
  const rules = useListTableDiscoveryRules();
  const ordered = useMemo(() => [...(rules.data ?? [])].sort(byEvaluationOrder), [rules.data]);
  const columns = useMemo(() => rulesColumns(), []);

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
