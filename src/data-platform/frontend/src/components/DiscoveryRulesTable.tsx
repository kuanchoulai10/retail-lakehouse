import {
  Badge,
  Button,
  createDataTableColumnHelper,
  DataTable,
  IconArrowDown,
  IconArrowUp,
  IconButton,
  IconTrash,
} from "@retail-lakehouse/design-system";
import { useMemo, type ReactNode } from "react";
import { outcomeLabel, type DiscoveryRuleDraft } from "@/lib/discoveryPolicyDraft";

export interface DiscoveryRuleActions {
  move: (rule: DiscoveryRuleDraft, by: -1 | 1) => void;
  edit: (rule: DiscoveryRuleDraft) => void;
  remove: (rule: DiscoveryRuleDraft) => void;
}

interface Props {
  // In the order they are read; a rule's position is its number.
  rules: DiscoveryRuleDraft[];
  readOnly: boolean;
  // Pass the same object across renders (memoise it), or every render remounts the row controls.
  actions?: DiscoveryRuleActions;
  // Text shown under a rule's conditions, keyed by the rule's `key`.
  hints?: Record<string, string[]>;
  emptyState?: ReactNode;
}

// One row: the rule with what its cells show besides it. Position, ends and hints travel in the
// data, not in the columns, so the columns (the cells' component types) change only with the actions.
interface RuleRow {
  rule: DiscoveryRuleDraft;
  position: number;
  last: boolean;
  hints: string[];
}

const NO_HINTS: Record<string, string[]> = {};

const column = createDataTableColumnHelper<RuleRow>();

function Globs({ globs }: { globs: string[] }) {
  if (globs.length === 0) return <span className="text-on-surface-variant">—</span>;
  return (
    <ul className="m-0 flex list-none flex-wrap gap-x-3 gap-y-1 p-0">
      {globs.map((glob) => (
        <li key={glob} className="font-mono whitespace-nowrap">
          {glob}
        </li>
      ))}
    </ul>
  );
}

function rulesColumns(actions: DiscoveryRuleActions | null) {
  const columns = [
    column.display({
      id: "position",
      header: "#",
      cell: (info) => <span className="tabular-nums">{info.row.original.position}</span>,
    }),
    column.display({
      id: "outcome",
      header: "Outcome",
      cell: (info) => <Badge className="whitespace-nowrap">{outcomeLabel(info.row.original.rule.outcome)}</Badge>,
    }),
    column.display({
      id: "namespace",
      header: "Namespace",
      cell: (info) => {
        const { rule, hints } = info.row.original;
        return (
          <div className="flex flex-col gap-1">
            <Globs globs={rule.namespaces} />
            {hints.map((note) => (
              <p key={note} className="type-body-small text-on-surface-variant">
                {note}
              </p>
            ))}
          </div>
        );
      },
    }),
    column.display({
      id: "tableName",
      header: "Table name",
      cell: (info) => <Globs globs={info.row.original.rule.tableNames} />,
    }),
  ];
  if (actions === null) return columns;
  return [
    ...columns,
    column.display({
      id: "actions",
      header: () => <span className="sr-only">Actions</span>,
      cell: (info) => {
        const { rule, position: at, last } = info.row.original;
        return (
          <div className="flex items-center justify-end gap-1">
            <IconButton
              styleType="ghost"
              shape="rectangle"
              aria-label={`Move rule ${at} up`}
              icon={<IconArrowUp />}
              disabled={at === 1}
              onClick={() => actions.move(rule, -1)}
            />
            <IconButton
              styleType="ghost"
              shape="rectangle"
              aria-label={`Move rule ${at} down`}
              icon={<IconArrowDown />}
              disabled={last}
              onClick={() => actions.move(rule, 1)}
            />
            <Button
              type="button"
              styleType="outlined"
              size="small"
              aria-label={`Edit rule ${at}`}
              onClick={() => actions.edit(rule)}
            >
              Edit
            </Button>
            <IconButton
              styleType="ghost"
              shape="rectangle"
              aria-label={`Delete rule ${at}`}
              icon={<IconTrash />}
              onClick={() => actions.remove(rule)}
            />
          </div>
        );
      },
    }),
  ];
}

// A discovery policy's rules, read top to bottom: the first whose conditions all hold decides.
export function DiscoveryRulesTable({ rules, readOnly, actions, hints = NO_HINTS, emptyState = "No rules." }: Props) {
  const rowActions = readOnly || actions === undefined ? null : actions;
  const columns = useMemo(() => rulesColumns(rowActions), [rowActions]);
  const rows = useMemo(
    () =>
      rules.map((rule, index) => ({
        rule,
        position: index + 1,
        last: index === rules.length - 1,
        hints: hints[rule.key] ?? [],
      })),
    [rules, hints],
  );
  return (
    <DataTable
      caption="Discovery rules, read top to bottom"
      columns={columns}
      data={rows}
      getRowId={(row) => row.rule.key}
      emptyState={emptyState}
    />
  );
}
