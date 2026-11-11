import {
  Badge,
  Banner,
  Button,
  createDataTableColumnHelper,
  DataTable,
  IconArrowDown,
  IconArrowUp,
  IconButton,
  IconTrash,
  Panel,
  Skeleton,
  Switch,
} from "@retail-lakehouse/design-system";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useRef, useState } from "react";
import {
  getGetTableDiscoveryRulesQueryKey,
  getPreviewTableDiscoveryRulesUrl,
  previewTableDiscoveryRules,
  replaceTableDiscoveryRules,
  useGetTableDiscoveryRules,
} from "@/api/generated/discovery-rules/discovery-rules";
import type { ReplaceTableDiscoveryRulesApiRequest } from "@/api/generated/model";
import { DiscoveryRuleEditor } from "@/components/DiscoveryRuleEditor";
import { DiscoveryRulesPreview } from "@/components/DiscoveryRulesPreview";
import { PageHeader } from "@/components/PageHeader";
import { errorMessage } from "@/format";
import {
  draftFromRule,
  inPriorityOrder,
  newRuleDraft,
  rulesRequest,
  type DiscoveryRuleDraft,
} from "@/lib/discoveryRuleDraft";
import { isConflict } from "@/lib/updateErrorMessage";
import { useDebouncedValue } from "@/lib/useDebouncedValue";

const SKELETON_ROWS = 3;
const PREVIEW_DELAY_MS = 300;
const CONFLICT_MESSAGE = "Someone else changed these rules. Reload to see their version.";

// The list the page edits, with the version it was read at: a refetch while the user edits
// must not move the version forward, or the save would overwrite a change made meanwhile.
interface Draft {
  version: number;
  rules: DiscoveryRuleDraft[];
}

interface Editing {
  mode: "add" | "edit";
  rule: DiscoveryRuleDraft;
}

interface RowActions {
  move: (rule: DiscoveryRuleDraft, by: -1 | 1) => void;
  edit: (rule: DiscoveryRuleDraft) => void;
  remove: (rule: DiscoveryRuleDraft) => void;
  setEnabled: (rule: DiscoveryRuleDraft, enabled: boolean) => void;
}

const column = createDataTableColumnHelper<DiscoveryRuleDraft>();

function capitalise(word: string): string {
  return word.charAt(0).toUpperCase() + word.slice(1);
}

function globsColumn(field: "catalogs" | "namespaces" | "tables", header: string) {
  return column.display({
    id: field,
    header,
    cell: (info) => (
      <ul className="m-0 flex list-none flex-wrap gap-1 p-0">
        {info.row.original[field].map((glob) => (
          <li key={glob}>
            <Badge className="font-mono whitespace-nowrap">{glob}</Badge>
          </li>
        ))}
      </ul>
    ),
  });
}

function rulesColumns(ordered: DiscoveryRuleDraft[], actions: RowActions) {
  return column.columns([
    column.display({
      id: "priority",
      header: "Priority",
      cell: (info) => <span className="tabular-nums">{info.row.original.priority}</span>,
    }),
    column.display({
      id: "action",
      header: "Action",
      cell: (info) => <Badge>{capitalise(info.row.original.action)}</Badge>,
    }),
    globsColumn("catalogs", "Catalogs"),
    globsColumn("namespaces", "Namespaces"),
    globsColumn("tables", "Tables"),
    column.display({
      id: "enabled",
      header: "State",
      cell: (info) => {
        const rule = info.row.original;
        return (
          <Switch
            label="Enabled"
            aria-label={`Rule ${rule.priority} enabled`}
            checked={rule.enabled}
            onCheckedChange={(checked) => actions.setEnabled(rule, checked)}
          />
        );
      },
    }),
    column.display({
      id: "actions",
      header: () => <span className="sr-only">Actions</span>,
      cell: (info) => {
        const rule = info.row.original;
        const index = ordered.indexOf(rule);
        return (
          <div className="flex items-center justify-end gap-1">
            <IconButton
              styleType="ghost"
              shape="rectangle"
              aria-label={`Move rule ${rule.priority} up`}
              icon={<IconArrowUp />}
              disabled={index === 0}
              onClick={() => actions.move(rule, -1)}
            />
            <IconButton
              styleType="ghost"
              shape="rectangle"
              aria-label={`Move rule ${rule.priority} down`}
              icon={<IconArrowDown />}
              disabled={index === ordered.length - 1}
              onClick={() => actions.move(rule, 1)}
            />
            <Button
              type="button"
              styleType="outlined"
              size="small"
              aria-label={`Edit rule ${rule.priority}`}
              onClick={() => actions.edit(rule)}
            >
              Edit
            </Button>
            <IconButton
              styleType="ghost"
              shape="rectangle"
              aria-label={`Delete rule ${rule.priority}`}
              icon={<IconTrash />}
              onClick={() => actions.remove(rule)}
            />
          </div>
        );
      },
    }),
  ]);
}

// Moving a rule trades priorities with its neighbour, so the order is always the priorities'.
function moved(rules: DiscoveryRuleDraft[], rule: DiscoveryRuleDraft, by: -1 | 1): DiscoveryRuleDraft[] {
  const ordered = inPriorityOrder(rules);
  const neighbour = ordered[ordered.indexOf(rule) + by];
  if (neighbour === undefined) return rules;
  return rules.map((r) => {
    if (r === rule) return { ...r, priority: neighbour.priority };
    if (r === neighbour) return { ...r, priority: rule.priority };
    return r;
  });
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
  const queryClient = useQueryClient();
  const saved = useGetTableDiscoveryRules();
  const base = useMemo<Draft | null>(
    () =>
      saved.data === undefined
        ? null
        : { version: saved.data.version, rules: inPriorityOrder(saved.data.rules.map(draftFromRule)) },
    [saved.data],
  );
  const [draft, setDraft] = useState<Draft | null>(null);
  const [editing, setEditing] = useState<Editing | null>(null);
  const [savedNotice, setSavedNotice] = useState(false);
  const newKeys = useRef(0);

  const current = draft ?? base;
  const ordered = useMemo(() => inPriorityOrder(current?.rules ?? []), [current]);
  const request = useMemo(() => rulesRequest(ordered), [ordered]);
  const dirty =
    draft !== null && base !== null && JSON.stringify(request) !== JSON.stringify(rulesRequest(base.rules));

  const settledRequest = useDebouncedValue(request, PREVIEW_DELAY_MS);
  const previewSettled = settledRequest === request;
  const preview = useQuery({
    queryKey: [getPreviewTableDiscoveryRulesUrl(), { rules: settledRequest }],
    queryFn: ({ signal }) => previewTableDiscoveryRules({ rules: settledRequest }, { signal }),
    enabled: current !== null && previewSettled,
    placeholderData: keepPreviousData,
    retry: false,
  });

  const save = useMutation({
    mutationFn: (body: ReplaceTableDiscoveryRulesApiRequest) => replaceTableDiscoveryRules(body),
    // A write can fail after part of it landed, so the page refetches either way; the draft is
    // dropped only once the save succeeded, so a refused save keeps the user's edits.
    onSettled: async (_data, error) => {
      await queryClient.invalidateQueries({ queryKey: getGetTableDiscoveryRulesQueryKey() });
      if (error === null) {
        setDraft(null);
        setSavedNotice(true);
      }
    },
  });

  function change(edit: (rules: DiscoveryRuleDraft[]) => DiscoveryRuleDraft[]) {
    if (current === null) return;
    setDraft({ version: current.version, rules: edit(current.rules) });
    setSavedNotice(false);
    if (!isConflict(save.error)) save.reset();
  }

  const actions: RowActions = {
    move: (rule, by) => change((rules) => moved(rules, rule, by)),
    edit: (rule) => setEditing({ mode: "edit", rule }),
    remove: (rule) => change((rules) => rules.filter((r) => r !== rule)),
    setEnabled: (rule, enabled) => change((rules) => rules.map((r) => (r === rule ? { ...r, enabled } : r))),
  };
  const columns = rulesColumns(ordered, actions);

  function addRule() {
    newKeys.current += 1;
    setEditing({ mode: "add", rule: newRuleDraft(current?.rules ?? [], `new-${newKeys.current}`) });
  }

  function applyEdit(rule: DiscoveryRuleDraft) {
    const mode = editing?.mode;
    change((rules) => (mode === "add" ? [...rules, rule] : rules.map((r) => (r.key === rule.key ? rule : r))));
    setEditing(null);
  }

  function submit() {
    if (current === null) return;
    setSavedNotice(false);
    save.mutate({ version: current.version, rules: request });
  }

  function discard() {
    setDraft(null);
    save.reset();
  }

  function reload() {
    discard();
    void queryClient.invalidateQueries({ queryKey: getGetTableDiscoveryRulesQueryKey() });
  }

  return (
    <section>
      <PageHeader title="Discovery rules">
        <span>Lowest priority first; the first enabled rule that matches a table decides.</span>
      </PageHeader>
      {saved.isError && (
        <Banner type="negative" title={`Could not load discovery rules: ${errorMessage(saved.error)}`} />
      )}
      {!saved.isError && (
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center justify-end gap-2">
            {dirty && <span className="type-body-small mr-auto text-on-surface-variant">Unsaved changes</span>}
            <Button type="button" styleType="outlined" disabled={!dirty || save.isPending} onClick={discard}>
              Discard changes
            </Button>
            <Button type="button" disabled={!dirty || save.isPending} isLoading={save.isPending} onClick={submit}>
              Save
            </Button>
          </div>
          {savedNotice && <Banner type="information" title="Saved. Discovering tables…" />}
          {save.isError && (
            <div className="flex flex-wrap items-center gap-3">
              <Banner
                type="negative"
                title={isConflict(save.error) ? CONFLICT_MESSAGE : errorMessage(save.error)}
                className="min-w-0 flex-1"
              />
              {isConflict(save.error) && (
                <Button type="button" styleType="outlined" size="small" onClick={reload}>
                  Reload
                </Button>
              )}
            </div>
          )}
          <div className="grid min-w-0 grid-cols-1 gap-4 xl:grid-cols-3">
            <Panel
              title="Rules"
              className="min-w-0 xl:col-span-2"
              aria-busy={saved.isPending}
              actions={
                <Button type="button" size="small" disabled={current === null} onClick={addRule}>
                  Add rule
                </Button>
              }
            >
              <DataTable
                caption="Discovery rules in evaluation order"
                columns={columns}
                data={ordered}
                getRowId={(rule) => rule.key}
                emptyState={saved.isPending ? <LoadingRows /> : "No discovery rules. No table is managed."}
              />
            </Panel>
            <DiscoveryRulesPreview
              rules={ordered}
              preview={preview.data}
              isFetching={current === null || !previewSettled || preview.isFetching}
              error={preview.error}
            />
          </div>
        </div>
      )}
      {editing !== null && (
        <DiscoveryRuleEditor
          title={editing.mode === "add" ? "Add rule" : "Edit rule"}
          submitLabel={editing.mode === "add" ? "Add rule" : "Update rule"}
          rule={editing.rule}
          onSubmit={applyEdit}
          onClose={() => setEditing(null)}
        />
      )}
    </section>
  );
}
