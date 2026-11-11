import { Banner, Panel, Skeleton } from "@retail-lakehouse/design-system";
import type {
  DiscoveryPreviewTableApiResponse,
  PreviewTableDiscoveryRulesApiResponse,
} from "@/api/generated/model";
import { errorMessage } from "@/format";
import { inPriorityOrder, previewRuleId, type DiscoveryRuleDraft } from "@/lib/discoveryRuleDraft";

interface Props {
  // The draft the preview was asked for; its order and ids name the deciding rules.
  rules: DiscoveryRuleDraft[];
  preview: PreviewTableDiscoveryRulesApiResponse | undefined;
  isFetching: boolean;
  error: unknown;
}

interface Group {
  key: string;
  title: string;
  managed: boolean;
  tables: DiscoveryPreviewTableApiResponse[];
}

function plural(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? "" : "s"}`;
}

// One group per deciding rule, in priority order, then the tables no rule matches.
function groupsOf(rules: DiscoveryRuleDraft[], tables: DiscoveryPreviewTableApiResponse[]): Group[] {
  const ruleGroups = inPriorityOrder(rules).map((rule, index): Group => {
    const id = previewRuleId(rule, index);
    return {
      key: id,
      title: `Priority ${rule.priority}, ${rule.action}${rule.id === null ? " (unsaved)" : ""}`,
      managed: rule.action === "include",
      tables: tables.filter((table) => table.rule_id === id),
    };
  });
  const unmatched: Group = {
    key: "none",
    title: "No rule matches",
    managed: false,
    tables: tables.filter((table) => table.rule_id === null),
  };
  return [...ruleGroups, unmatched].filter((group) => group.tables.length > 0);
}

function label(group: Group): string {
  return `${group.title}: ${plural(group.tables.length, "table")}, ${group.managed ? "managed" : "unmanaged"}`;
}

function PreviewGroup({ group, showCatalog }: { group: Group; showCatalog: boolean }) {
  return (
    <div role="group" aria-label={label(group)} className="flex flex-col gap-1">
      <h3 className="type-label-large flex flex-wrap items-baseline gap-x-2">
        <span>{group.title}</span>
        <span className="type-body-small text-on-surface-variant">
          {plural(group.tables.length, "table")}, {group.managed ? "managed" : "unmanaged"}
        </span>
      </h3>
      <ul className="m-0 flex list-none flex-col gap-0.5 p-0">
        {group.tables.map((table) => (
          <li
            key={`${table.catalog}\u001f${table.namespace}\u001f${table.table}`}
            className="type-body-small flex min-w-0 gap-2 font-mono break-all"
          >
            {showCatalog && <span className="text-on-surface-variant">{table.catalog}</span>}
            <span>{`${table.namespace}.${table.table}`}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// Which tables the unsaved list would manage, grouped by the rule that decides each one.
export function DiscoveryRulesPreview({ rules, preview, isFetching, error }: Props) {
  const showCatalog = new Set(preview?.tables.map((table) => table.catalog)).size > 1;
  return (
    <Panel title="Preview" aria-busy={isFetching} className="flex min-w-0 flex-col gap-3">
      {error !== null && error !== undefined && (
        <Banner type="negative" title={`Could not preview these rules: ${errorMessage(error)}`} />
      )}
      {preview === undefined && error == null && (
        <div className="grid gap-2">
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
        </div>
      )}
      {preview !== undefined && (
        <>
          <p className="type-body-medium tabular-nums">
            {`${preview.managed} managed, ${preview.unmanaged} unmanaged`}
          </p>
          {preview.tables.length === 0 && (
            <p className="type-body-small text-on-surface-variant">No tables in the covered catalogs.</p>
          )}
          {groupsOf(rules, preview.tables).map((group) => (
            <PreviewGroup key={group.key} group={group} showCatalog={showCatalog} />
          ))}
        </>
      )}
    </Panel>
  );
}
