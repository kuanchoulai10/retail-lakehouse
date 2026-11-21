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
import type { ReactNode } from "react";
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
  actions?: DiscoveryRuleActions;
  // Text shown under a rule's conditions, keyed by the rule's `key`.
  hints?: Record<string, string[]>;
  emptyState?: ReactNode;
}

const column = createDataTableColumnHelper<DiscoveryRuleDraft>();

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

function rulesColumns(rules: DiscoveryRuleDraft[], hints: Record<string, string[]>, actions: DiscoveryRuleActions | null) {
  const position = (rule: DiscoveryRuleDraft) => rules.indexOf(rule) + 1;
  const columns = [
    column.display({
      id: "position",
      header: "#",
      cell: (info) => <span className="tabular-nums">{position(info.row.original)}</span>,
    }),
    column.display({
      id: "outcome",
      header: "Outcome",
      cell: (info) => <Badge className="whitespace-nowrap">{outcomeLabel(info.row.original.outcome)}</Badge>,
    }),
    column.display({
      id: "namespace",
      header: "Namespace",
      cell: (info) => {
        const rule = info.row.original;
        const notes = hints[rule.key] ?? [];
        return (
          <div className="flex flex-col gap-1">
            <Globs globs={rule.namespaces} />
            {notes.map((note) => (
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
      cell: (info) => <Globs globs={info.row.original.tableNames} />,
    }),
  ];
  if (actions === null) return columns;
  return [
    ...columns,
    column.display({
      id: "actions",
      header: () => <span className="sr-only">Actions</span>,
      cell: (info) => {
        const rule = info.row.original;
        const at = position(rule);
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
              disabled={at === rules.length}
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
export function DiscoveryRulesTable({ rules, readOnly, actions, hints = {}, emptyState = "No rules." }: Props) {
  const columns = rulesColumns(rules, hints, readOnly || actions === undefined ? null : actions);
  return (
    <DataTable
      caption="Discovery rules, read top to bottom"
      columns={columns}
      data={rules}
      getRowId={(rule) => rule.key}
      emptyState={emptyState}
    />
  );
}
