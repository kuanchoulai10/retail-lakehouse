import { Badge, createDataTableColumnHelper, DataTable } from "@retail-lakehouse/design-system";
import { useMemo, type ReactNode } from "react";
import { actionLabel, type DiscoveryRuleDraft } from "@/lib/discoveryPolicyDraft";

interface Props {
  // In the order they are read; a rule's position is its number.
  rules: DiscoveryRuleDraft[];
  emptyState?: ReactNode;
}

interface RuleRow {
  rule: DiscoveryRuleDraft;
  position: number;
}

const column = createDataTableColumnHelper<RuleRow>();

const COLUMNS = [
  column.display({
    id: "position",
    header: "#",
    cell: (info) => <span className="tabular-nums">{info.row.original.position}</span>,
  }),
  column.display({
    id: "action",
    header: "Action",
    cell: (info) => <Badge className="whitespace-nowrap">{actionLabel(info.row.original.rule.action)}</Badge>,
  }),
  column.display({
    id: "tableNamePattern",
    header: "Table name pattern",
    cell: (info) => <span className="font-mono break-all">{info.row.original.rule.tableNamePattern}</span>,
  }),
];

// A discovery policy's rules, read only, top to bottom: the last whose pattern matches a table decides it.
export function DiscoveryRulesTable({ rules, emptyState = "No rules." }: Props) {
  const rows = useMemo(() => rules.map((rule, index) => ({ rule, position: index + 1 })), [rules]);
  return (
    <DataTable
      caption="Discovery rules, read top to bottom"
      columns={COLUMNS}
      data={rows}
      getRowId={(row) => row.rule.key}
      emptyState={emptyState}
    />
  );
}
