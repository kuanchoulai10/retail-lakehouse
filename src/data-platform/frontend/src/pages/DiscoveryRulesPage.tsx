import {
  Banner,
  createDataTableColumnHelper,
  DataTable,
  Skeleton,
} from "@retail-lakehouse/design-system";
import { useMemo } from "react";
import { useGetTableDiscoveryRules } from "@/api/generated/discovery-rules/discovery-rules";
import type { TableDiscoveryRuleApiResponse } from "@/api/generated/model";
import { PageHeader } from "@/components/PageHeader";
import { errorMessage, formatTimestamp } from "@/format";

const SKELETON_ROWS = 3;

const column = createDataTableColumnHelper<TableDiscoveryRuleApiResponse>();

function capitalise(word: string): string {
  return word.charAt(0).toUpperCase() + word.slice(1);
}

function byPriority(a: TableDiscoveryRuleApiResponse, b: TableDiscoveryRuleApiResponse): number {
  return a.priority - b.priority;
}

function globsColumn(field: "catalogs" | "namespaces" | "tables", header: string) {
  return column.accessor((rule) => rule[field].join(", "), {
    id: field,
    header,
    enableSorting: false,
    cell: (info) => <span className="type-code whitespace-nowrap">{info.getValue()}</span>,
  });
}

function rulesColumns() {
  return column.columns([
    column.accessor("priority", {
      header: "Priority",
      enableSorting: false,
      cell: (info) => <span className="tabular-nums">{info.getValue()}</span>,
    }),
    column.accessor("action", { header: "Action", enableSorting: false, cell: (info) => capitalise(info.getValue()) }),
    globsColumn("catalogs", "Catalogs"),
    globsColumn("namespaces", "Namespaces"),
    globsColumn("tables", "Tables"),
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

export function DiscoveryRulesPage() {
  const rules = useGetTableDiscoveryRules();
  const ordered = useMemo(() => [...(rules.data?.rules ?? [])].sort(byPriority), [rules.data]);
  const columns = useMemo(() => rulesColumns(), []);

  return (
    <section>
      <PageHeader title="Discovery rules">
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
