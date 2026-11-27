import {
  createDataTableColumnHelper,
  DataTable,
  IconArrowDown,
  IconArrowUp,
  IconButton,
  IconTrash,
  Select,
  TextField,
} from "@retail-lakehouse/design-system";
import { useCallback, useEffect, useId, useLayoutEffect, useMemo, useRef } from "react";
import { movedRule, type DiscoveryRuleDraft, type RuleAction } from "@/lib/discoveryPolicyDraft";
import { RULE_ACTION_OPTIONS } from "./forms/ruleActionOptions";

type RulesEdit = (rules: DiscoveryRuleDraft[]) => DiscoveryRuleDraft[];

interface Props {
  // In the order they are read; a rule's position is its number.
  rules: DiscoveryRuleDraft[];
  // Called with an edit of the rules, so every change applies to the page's latest draft.
  onChange: (edit: RulesEdit) => void;
  // The rule whose pattern field takes focus, such as one just added.
  focusKey?: string | null;
}

// One row: the rule with what its cells show and do besides it. `change` travels in the data, not in
// the columns, so the columns (the cells' component types) never change.
interface RuleRow {
  rule: DiscoveryRuleDraft;
  position: number;
  last: boolean;
  change: (edit: RulesEdit) => void;
}

const column = createDataTableColumnHelper<RuleRow>();

function patternFieldId(baseId: string, key: string): string {
  return `${baseId}-pattern-${key}`;
}

function replaced(rules: DiscoveryRuleDraft[], rule: DiscoveryRuleDraft): DiscoveryRuleDraft[] {
  return rules.map((r) => (r.key === rule.key ? rule : r));
}

// The columns are built once: a cell's component type must stay the same across renders, or every
// keystroke would remount the fields under the cursor. Each cell reads its rule and `change` from
// the row.
function editorColumns(baseId: string) {
  return [
    column.display({
      id: "position",
      header: "#",
      cell: (info) => <span className="tabular-nums">{info.row.original.position}</span>,
    }),
    column.display({
      id: "action",
      header: "Action",
      cell: (info) => {
        const { rule, position, change } = info.row.original;
        return (
          <Select
            label={`Action of rule ${position}`}
            hideLabel
            value={rule.action}
            items={RULE_ACTION_OPTIONS}
            className="min-w-32"
            onValueChange={(action) => change((rules) => replaced(rules, { ...rule, action: action as RuleAction }))}
          />
        );
      },
    }),
    column.display({
      id: "tableNamePattern",
      header: "Table name pattern",
      cell: (info) => {
        const { rule, position, change } = info.row.original;
        return (
          <TextField
            id={patternFieldId(baseId, rule.key)}
            label={`Table name pattern of rule ${position}`}
            hideLabel
            autoComplete="off"
            placeholder="orders_*"
            className="min-w-40 font-mono"
            value={rule.tableNamePattern}
            onChange={(event) => {
              const tableNamePattern = event.target.value;
              change((rules) => replaced(rules, { ...rule, tableNamePattern }));
            }}
          />
        );
      },
    }),
    column.display({
      id: "actions",
      header: () => <span className="sr-only">Actions</span>,
      cell: (info) => {
        const { rule, position, last, change } = info.row.original;
        return (
          <div className="flex items-center justify-end gap-1">
            <IconButton
              styleType="ghost"
              shape="rectangle"
              aria-label={`Move rule ${position} up`}
              icon={<IconArrowUp />}
              disabled={position === 1}
              onClick={() => change((rules) => movedRule(rules, rule.key, -1))}
            />
            <IconButton
              styleType="ghost"
              shape="rectangle"
              aria-label={`Move rule ${position} down`}
              icon={<IconArrowDown />}
              disabled={last}
              onClick={() => change((rules) => movedRule(rules, rule.key, 1))}
            />
            <IconButton
              styleType="ghost"
              shape="rectangle"
              aria-label={`Delete rule ${position}`}
              icon={<IconTrash />}
              onClick={() => change((rules) => rules.filter((r) => r.key !== rule.key))}
            />
          </div>
        );
      },
    }),
  ];
}

// A discovery policy's rules as the page's draft edits them, one row per rule: its action, its table
// name pattern, and buttons to move or delete it. The page saves the whole policy.
export function DiscoveryRuleEditor({ rules, onChange, focusKey = null }: Props) {
  const baseId = useId();
  const latestOnChange = useRef(onChange);
  useLayoutEffect(() => {
    latestOnChange.current = onChange;
  });
  const change = useCallback((edit: RulesEdit) => latestOnChange.current(edit), []);
  const columns = useMemo(() => editorColumns(baseId), [baseId]);
  const rows = useMemo(
    () => rules.map((rule, index) => ({ rule, position: index + 1, last: index === rules.length - 1, change })),
    [rules, change],
  );

  useEffect(() => {
    if (focusKey !== null) document.getElementById(patternFieldId(baseId, focusKey))?.focus();
  }, [baseId, focusKey]);

  return (
    <DataTable
      caption="Discovery rules, read top to bottom"
      columns={columns}
      data={rows}
      getRowId={(row) => row.rule.key}
      emptyState="No rules. A policy needs at least one."
    />
  );
}
