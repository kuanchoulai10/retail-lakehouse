import { Banner, Button, DescriptionList, TextArea, TextLink } from "@retail-lakehouse/design-system";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router";
import {
  getGetTableDiscoveryPolicyQueryKey,
  getListTableDiscoveryPoliciesQueryKey,
  updateTableDiscoveryPolicy,
  useGetTableDiscoveryPolicy,
} from "@/api/generated/discovery-policies/discovery-policies";
import type { TableDiscoveryPolicyApiResponse, UpdateTableDiscoveryPolicyApiRequest } from "@/api/generated/model";
import { DiscoveryRuleEditor } from "@/components/DiscoveryRuleEditor";
import { DiscoveryRulesTable } from "@/components/DiscoveryRulesTable";
import { SelectField, type SelectOption } from "@/components/forms/SelectField";
import { PageHeader } from "@/components/PageHeader";
import { PanelSkeleton } from "@/components/PanelSkeleton";
import { errorMessage, formatTimestamp } from "@/format";
import { discoveryPoliciesPath, discoveryPolicyVersionPath } from "@/lib/discoveryPolicyPaths";
import {
  draftFromPolicy,
  movedRule,
  newRuleDraft,
  outcomeLabel,
  updateRequest,
  type DiscoveryOutcome,
  type DiscoveryPolicyDraft,
  type DiscoveryRuleDraft,
} from "@/lib/discoveryPolicyDraft";
import { isConflict } from "@/lib/updateErrorMessage";

const CONFLICT_MESSAGE = "Someone else changed this policy. Reload to see their version.";
const VISIBLE_VERSIONS = 10;
const OUTCOMES: SelectOption<DiscoveryOutcome>[] = [
  { value: "manage", label: "Manage" },
  { value: "unmanage", label: "Do not manage" },
];

type Policy = TableDiscoveryPolicyApiResponse;

interface Editing {
  mode: "add" | "edit";
  rule: DiscoveryRuleDraft;
}

// The content the API would store, without the version, so a draft equal to what is saved is not dirty.
function contentKey(draft: DiscoveryPolicyDraft): string {
  return JSON.stringify({ ...updateRequest(draft), version: null });
}

// Every kept version, newest first, each linking to its page; a long history folds behind a button,
// which hands focus to the first version it reveals.
function VersionLinks({ name, latest }: { name: string; latest: number }) {
  const [revealed, setRevealed] = useState(false);
  const list = useRef<HTMLUListElement>(null);
  const focusRevealed = useRef(false);
  const versions = Array.from({ length: latest }, (_, index) => latest - index);
  const hidden = versions.length - VISIBLE_VERSIONS;
  const shown = revealed ? versions : versions.slice(0, VISIBLE_VERSIONS);

  useEffect(() => {
    if (revealed && focusRevealed.current) list.current?.querySelectorAll("a")[VISIBLE_VERSIONS]?.focus();
  }, [revealed]);

  return (
    <nav aria-label="Versions" className="flex flex-wrap items-center gap-x-3 gap-y-1">
      <ul ref={list} className="m-0 flex list-none flex-wrap gap-x-3 gap-y-1 p-0">
        {shown.map((version) => (
          <li key={version}>
            <TextLink asChild>
              <Link to={discoveryPolicyVersionPath(name, version)}>{`v${version}`}</Link>
            </TextLink>
          </li>
        ))}
      </ul>
      {!revealed && hidden > 0 && (
        <Button
          type="button"
          styleType="ghost"
          size="small"
          onClick={() => {
            focusRevealed.current = true;
            setRevealed(true);
          }}
        >
          {`Show ${hidden} earlier version${hidden === 1 ? "" : "s"}`}
        </Button>
      )}
    </nav>
  );
}

// The platform default has fixed content: the page shows it and offers nothing to change.
function DefaultPolicy({ policy }: { policy: Policy }) {
  const draft = draftFromPolicy(policy);
  return (
    <div className="flex flex-col gap-4">
      <Banner type="information" title="The platform default decides wherever no other policy is attached. It cannot be changed.">
        {policy.description}
      </Banner>
      <DescriptionList items={[{ term: "When no rule matches", description: outcomeLabel(draft.noMatchOutcome) }]} />
      <DiscoveryRulesTable rules={draft.rules} readOnly />
    </div>
  );
}

// The policy's content as a page-level draft, saved whole with the version it was read at.
function PolicyDraftEditor({ policy }: { policy: Policy }) {
  const queryClient = useQueryClient();
  const base = useMemo(() => draftFromPolicy(policy), [policy]);
  // A refetch while the user edits must not move the draft's version forward, or the save would
  // overwrite a change made meanwhile; Reload drops the draft on purpose.
  const [draft, setDraft] = useState<DiscoveryPolicyDraft | null>(null);
  const [editing, setEditing] = useState<Editing | null>(null);
  const [savedNotice, setSavedNotice] = useState(false);
  const newKeys = useRef(0);
  const rulesHeadingId = useId();

  const current = draft ?? base;
  const dirty = draft !== null && contentKey(draft) !== contentKey(base);

  const save = useMutation({
    mutationFn: (body: UpdateTableDiscoveryPolicyApiRequest) => updateTableDiscoveryPolicy(policy.name, body),
    // A write can fail after part of it landed, so the page refetches either way; the draft is
    // dropped only once the save succeeded, so a refused save keeps the user's edits.
    onSettled: async (_data, error) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: getGetTableDiscoveryPolicyQueryKey(policy.name) }),
        queryClient.invalidateQueries({ queryKey: getListTableDiscoveryPoliciesQueryKey(), exact: true }),
      ]);
      if (error === null) {
        setDraft(null);
        setSavedNotice(true);
      }
    },
  });

  function change(edit: (draft: DiscoveryPolicyDraft) => DiscoveryPolicyDraft) {
    setDraft(edit(current));
    setSavedNotice(false);
    if (!isConflict(save.error)) save.reset();
  }

  function changeRules(edit: (rules: DiscoveryRuleDraft[]) => DiscoveryRuleDraft[]) {
    change((d) => ({ ...d, rules: edit(d.rules) }));
  }

  function addRule() {
    newKeys.current += 1;
    setEditing({ mode: "add", rule: newRuleDraft(`new-${newKeys.current}`) });
  }

  function applyEdit(rule: DiscoveryRuleDraft) {
    const mode = editing?.mode;
    changeRules((rules) => (mode === "add" ? [...rules, rule] : rules.map((r) => (r.key === rule.key ? rule : r))));
    setEditing(null);
  }

  function submit() {
    setSavedNotice(false);
    save.mutate(updateRequest(current));
  }

  function discard() {
    setDraft(null);
    save.reset();
  }

  function reload() {
    discard();
    void queryClient.invalidateQueries({ queryKey: getGetTableDiscoveryPolicyQueryKey(policy.name) });
  }

  return (
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
      <div className="grid grid-cols-1 gap-4 md:max-w-xl">
        <TextArea
          label="Description"
          value={current.description}
          onChange={(event) => change((d) => ({ ...d, description: event.target.value }))}
        />
        <SelectField
          label="When no rule matches"
          value={current.noMatchOutcome}
          options={OUTCOMES}
          onChange={(noMatchOutcome) => change((d) => ({ ...d, noMatchOutcome }))}
        />
      </div>
      {/* Unframed, like the Tables page: the table's own header row separates it from the page. */}
      <section aria-labelledby={rulesHeadingId} className="flex min-w-0 flex-col gap-3">
        <header className="flex flex-wrap items-center justify-between gap-2">
          <h2 id={rulesHeadingId} className="type-title-small">
            Rules
          </h2>
          <Button type="button" size="small" onClick={addRule}>
            Add rule
          </Button>
        </header>
        <DiscoveryRulesTable
          rules={current.rules}
          readOnly={false}
          actions={{
            move: (rule, by) => changeRules((rules) => movedRule(rules, rule.key, by)),
            edit: (rule) => setEditing({ mode: "edit", rule }),
            remove: (rule) => changeRules((rules) => rules.filter((r) => r.key !== rule.key)),
          }}
          emptyState={`No rules. ${outcomeLabel(current.noMatchOutcome)} every table.`}
        />
      </section>
      {editing !== null && (
        <DiscoveryRuleEditor
          title={editing.mode === "add" ? "Add rule" : "Edit rule"}
          submitLabel={editing.mode === "add" ? "Add rule" : "Update rule"}
          rule={editing.rule}
          onSubmit={applyEdit}
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  );
}

// One discovery policy: its versions, and its content to edit as a draft (the default only reads).
export function DiscoveryPolicyPage() {
  const { name = "" } = useParams();
  const query = useGetTableDiscoveryPolicy(name);
  const policy = query.data;

  const header = (
    <PageHeader title={name} breadcrumbs={[{ label: "Discovery policies", to: discoveryPoliciesPath() }, { label: name }]}>
      {policy !== undefined && (
        <>
          <span>
            Version {policy.version}, saved <time dateTime={policy.updated_at}>{formatTimestamp(policy.updated_at)}</time>
          </span>
          <VersionLinks name={policy.name} latest={policy.version} />
        </>
      )}
    </PageHeader>
  );

  if (query.isPending) return <PanelSkeleton label={`Loading discovery policy ${name}…`} />;
  if (query.isError || policy === undefined) {
    return (
      <section>
        {header}
        <Banner type="negative" title={`Could not load discovery policy ${name}: ${errorMessage(query.error)}`} />
      </section>
    );
  }
  return (
    <section>
      {header}
      {policy.is_default ? <DefaultPolicy policy={policy} /> : <PolicyDraftEditor key={policy.name} policy={policy} />}
    </section>
  );
}
