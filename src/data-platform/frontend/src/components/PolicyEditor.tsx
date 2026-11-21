import { Button, Switch, TextField, TextLink } from "@retail-lakehouse/design-system";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import {
  createTableMaintenancePolicy,
  getGetTableMaintenancePolicyQueryKey,
  getListTableMaintenancePoliciesQueryKey,
  getTableMaintenancePolicy,
  updateTableMaintenancePolicy,
} from "@/api/generated/maintenance-policies/maintenance-policies";
import type { RewriteDataFilesTargetApiRequestPer, TableMaintenancePolicyApiResponse } from "@/api/generated/model";
import { invalidateEffectivePolicies } from "@/api/invalidateEffectivePolicies";
import { errorMessage } from "@/format";
import {
  contentFromDraft,
  draftFromContent,
  includeOperation,
  type OperationKey,
  POLICY_NAME_PATTERN,
  type PolicyContent,
  type PolicyDraft,
} from "@/lib/policyDraft";
import { isConflict } from "@/lib/updateErrorMessage";
import { FormDialog } from "./forms/FormDialog";
import { ON_OFF, OptionSelectField } from "./forms/OptionSelectField";
import { SelectField, type SelectOption } from "./forms/SelectField";
import { OperationPolicySection } from "./OperationPolicySection";
import { WholeNumberField } from "./forms/WholeNumberField";

const CONFLICT_MESSAGE = "Someone else changed this policy. Reload to see their version.";
const NAME_MESSAGE = "A name uses letters, digits, - and _ only, at most 64 characters.";
const PER: SelectOption<RewriteDataFilesTargetApiRequestPer>[] = [
  { value: "partition", label: "Each partition" },
  { value: "table", label: "Whole table" },
];
const STRATEGIES: SelectOption<"binpack" | "sort">[] = [
  { value: "binpack", label: "Binpack" },
  { value: "sort", label: "Sort" },
];
const PREFIX_MISMATCH_MODES: SelectOption<"ERROR" | "IGNORE" | "DELETE">[] = [
  { value: "ERROR", label: "Error" },
  { value: "IGNORE", label: "Ignore" },
  { value: "DELETE", label: "Delete" },
];

interface Props {
  // The policy being edited, at the version `content` was read at; without one the editor
  // creates a policy.
  policy?: Pick<TableMaintenancePolicyApiResponse, "name" | "version">;
  // What the form starts from: the edited policy's content, or for a new policy the default
  // policy's, as the page passes it. The editor never makes values up.
  content: PolicyContent;
  // The platform default policy's content: an operation put into the policy with no target yet
  // starts from its target and options. Without it such an operation starts empty.
  defaults?: PolicyContent;
  onClose: () => void;
}

type Write =
  | { kind: "create"; name: string; content: PolicyContent }
  | { kind: "update"; name: string; version: number; content: PolicyContent };

export function PolicyEditor({ policy, content, defaults, onClose }: Props) {
  const queryClient = useQueryClient();
  // The version the edit started from; a refetch while the dialog is open must not move it
  // forward, or the save would overwrite a change made meanwhile. Reload moves it on purpose.
  const [loaded, setLoaded] = useState(() =>
    policy === undefined ? null : { name: policy.name, version: policy.version },
  );
  const [draft, setDraft] = useState<PolicyDraft>(() => draftFromContent(content));
  const [defaultDraft] = useState(() => (defaults === undefined ? null : draftFromContent(defaults)));
  const [name, setName] = useState("");
  const [invalid, setInvalid] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: (write: Write) =>
      write.kind === "create"
        ? createTableMaintenancePolicy({ ...write.content, name: write.name })
        : updateTableMaintenancePolicy(write.name, { ...write.content, version: write.version }),
    // A write can fail after part of it landed, so the page refetches either way; the dialog
    // closes only on success and otherwise keeps the user's edits with the API's message.
    onSettled: async (_data, error, write) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: getListTableMaintenancePoliciesQueryKey(), exact: true }),
        queryClient.invalidateQueries({ queryKey: getGetTableMaintenancePolicyQueryKey(write.name) }),
        invalidateEffectivePolicies(queryClient),
      ]);
      if (error === null) onClose();
    },
  });

  const reload = useMutation({
    mutationFn: (name: string) => getTableMaintenancePolicy(name),
    onSuccess: (latest) => {
      setLoaded({ name: latest.name, version: latest.version });
      setDraft(draftFromContent(latest));
      save.reset();
    },
  });

  function update<K extends keyof PolicyDraft>(key: K, change: Partial<PolicyDraft[K]> | PolicyDraft[K]) {
    setDraft((current) => ({
      ...current,
      [key]: typeof change === "object" ? { ...(current[key] as object), ...change } : change,
    }));
  }

  function include(key: OperationKey, included: boolean) {
    if (included) setDraft((current) => includeOperation(current, key, defaultDraft));
    else update(key, { included });
  }

  function submit() {
    if (loaded === null && !POLICY_NAME_PATTERN.test(name.trim())) {
      setInvalid(NAME_MESSAGE);
      return;
    }
    const result = contentFromDraft(draft);
    if ("error" in result) {
      setInvalid(result.error);
      return;
    }
    setInvalid(null);
    save.mutate(
      loaded === null
        ? { kind: "create", name: name.trim(), content: result.content }
        : { kind: "update", name: loaded.name, version: loaded.version, content: result.content },
    );
  }

  const conflict = loaded !== null && isConflict(save.error);
  const failure = save.isError ? (conflict ? CONFLICT_MESSAGE : errorMessage(save.error)) : null;
  const reloadFailure = reload.isError ? `Could not reload: ${errorMessage(reload.error)}` : null;
  const { rewriteDataFiles: data, rewriteManifests: manifests, expireSnapshots: snapshots, removeOrphanFiles: orphans } =
    draft;

  return (
    <FormDialog
      title={loaded === null ? "New policy" : "Edit policy"}
      description={
        loaded === null ? (
          "Starts from the default policy. A new policy applies to no table until it is attached."
        ) : (
          <>
            Saving <span className="font-mono">{loaded.name}</span> v{loaded.version} makes a new version. Every
            table it applies to follows it from its next reconciliation.
          </>
        )
      }
      submitLabel={loaded === null ? "Create policy" : "Save"}
      isPending={save.isPending || reload.isPending}
      error={invalid ?? reloadFailure ?? failure}
      errorAction={
        conflict && invalid === null ? (
          <Button
            type="button"
            styleType="outlined"
            size="small"
            disabled={reload.isPending}
            onClick={() => reload.mutate(loaded.name)}
          >
            Reload
          </Button>
        ) : undefined
      }
      onSubmit={submit}
      onClose={onClose}
    >
      {loaded === null && (
        <TextField
          label="Name"
          description="Letters, digits, - and _. A name cannot be changed later."
          autoComplete="off"
          className="font-mono"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      )}
      <TextField
        label="Description"
        autoComplete="off"
        value={draft.description}
        onChange={(event) => update("description", event.target.value)}
      />
      <WholeNumberField
        label="Check every (seconds)"
        unit="seconds"
        hint="Each table is checked at least this often, from 60 seconds to 7 days"
        value={draft.scheduleEvery}
        onChange={(value) => update("scheduleEvery", value)}
      />
      <Switch
        label="Check after catalog commits"
        checked={draft.catalogCommit}
        onCheckedChange={(catalogCommit) => update("catalogCommit", catalogCommit)}
      />
      {draft.catalogCommit && (
        <WholeNumberField
          label="Debounce (seconds)"
          unit="seconds"
          hint="The check runs this long after the first commit; later commits join it"
          value={draft.debounce}
          onChange={(value) => update("debounce", value)}
        />
      )}
      <div className="flex flex-col gap-1">
        <Switch label="Dry run" checked={draft.dryRun} onCheckedChange={(dryRun) => update("dryRun", dryRun)} />
        <p className="type-body-small text-on-surface-variant">
          Scheduled checks record what would run and start nothing; a manual run still runs.
        </p>
      </div>
      <p className="type-body-small text-on-surface-variant">
        Cooldowns and failure back-off are{" "}
        <TextLink asChild inline>
          <Link to="/platform-settings">platform settings</Link>
        </TextLink>
        .
      </p>

      <OperationPolicySection
        title="Rewrite data files"
        included={data.included}
        onIncludedChange={(included) => include("rewriteDataFiles", included)}
        target={
          <>
            <WholeNumberField
              label="Reducible files at most"
              hint="Files compaction would remove; a table over this is due"
              value={data.reducibleFilesAtMost}
              onChange={(reducibleFilesAtMost) => update("rewriteDataFiles", { reducibleFilesAtMost })}
            />
            <SelectField label="Per" value={data.per} options={PER} onChange={(per) => update("rewriteDataFiles", { per })} />
            <p className="type-body-small text-on-surface-variant">
              Files are sized to the table&apos;s <span className="font-mono">write.target-file-size-bytes</span>, else
              512 MiB.
            </p>
          </>
        }
        options={
          <>
            <OptionSelectField
              label="Strategy"
              value={data.strategy}
              options={STRATEGIES}
              onChange={(strategy) => update("rewriteDataFiles", { strategy })}
            />
            <TextField
              label="Sort order"
              description="Only with the sort strategy, such as id DESC NULLS LAST"
              autoComplete="off"
              className="font-mono"
              value={data.sortOrder}
              onChange={(event) => update("rewriteDataFiles", { sortOrder: event.target.value })}
            />
            <WholeNumberField
              label="Min input files"
              value={data.minInputFiles}
              onChange={(minInputFiles) => update("rewriteDataFiles", { minInputFiles })}
            />
            <OptionSelectField
              label="Partial progress"
              value={data.partialProgressEnabled}
              options={ON_OFF}
              onChange={(partialProgressEnabled) => update("rewriteDataFiles", { partialProgressEnabled })}
            />
            <WholeNumberField
              label="Partial progress max commits"
              hint="Only with partial progress on"
              value={data.partialProgressMaxCommits}
              onChange={(partialProgressMaxCommits) => update("rewriteDataFiles", { partialProgressMaxCommits })}
            />
            <WholeNumberField
              label="Max concurrent file group rewrites"
              value={data.maxConcurrentFileGroupRewrites}
              onChange={(maxConcurrentFileGroupRewrites) =>
                update("rewriteDataFiles", { maxConcurrentFileGroupRewrites })
              }
            />
            <OptionSelectField
              label="Rewrite all"
              value={data.rewriteAll}
              options={ON_OFF}
              onChange={(rewriteAll) => update("rewriteDataFiles", { rewriteAll })}
            />
            <WholeNumberField
              label="Delete file threshold"
              value={data.deleteFileThreshold}
              onChange={(deleteFileThreshold) => update("rewriteDataFiles", { deleteFileThreshold })}
            />
            <OptionSelectField
              label="Remove dangling deletes"
              value={data.removeDanglingDeletes}
              options={ON_OFF}
              onChange={(removeDanglingDeletes) => update("rewriteDataFiles", { removeDanglingDeletes })}
            />
            <WholeNumberField
              label="Max file group size (bytes)"
              unit="bytes"
              value={data.maxFileGroupSizeBytes}
              onChange={(maxFileGroupSizeBytes) => update("rewriteDataFiles", { maxFileGroupSizeBytes })}
            />
          </>
        }
      />

      <OperationPolicySection
        title="Rewrite manifests"
        included={manifests.included}
        onIncludedChange={(included) => include("rewriteManifests", included)}
        target={
          <WholeNumberField
            label="Small manifests at most"
            hint={
              <>
                Manifests under the table&apos;s <span className="font-mono">commit.manifest.target-size-bytes</span>,
                else 8 MiB
              </>
            }
            value={manifests.smallManifestsAtMost}
            onChange={(smallManifestsAtMost) => update("rewriteManifests", { smallManifestsAtMost })}
          />
        }
        options={
          <OptionSelectField
            label="Use caching"
            value={manifests.useCaching}
            options={ON_OFF}
            onChange={(useCaching) => update("rewriteManifests", { useCaching })}
          />
        }
      />

      <OperationPolicySection
        title="Expire snapshots"
        included={snapshots.included}
        onIncludedChange={(included) => include("expireSnapshots", included)}
        target={
          <>
            <WholeNumberField
              label="Min snapshots to keep"
              hint={
                <>
                  Empty: the table&apos;s <span className="font-mono">history.expire.min-snapshots-to-keep</span>, else 1
                </>
              }
              value={snapshots.minSnapshotsToKeep}
              onChange={(minSnapshotsToKeep) => update("expireSnapshots", { minSnapshotsToKeep })}
            />
            <WholeNumberField
              label="Max snapshot age (seconds)"
              unit="seconds"
              hint={
                <>
                  Empty: the table&apos;s <span className="font-mono">history.expire.max-snapshot-age-ms</span>, else 5
                  days
                </>
              }
              value={snapshots.maxSnapshotAge}
              onChange={(maxSnapshotAge) => update("expireSnapshots", { maxSnapshotAge })}
            />
          </>
        }
        options={
          <>
            <WholeNumberField
              label="Max concurrent deletes"
              value={snapshots.maxConcurrentDeletes}
              onChange={(maxConcurrentDeletes) => update("expireSnapshots", { maxConcurrentDeletes })}
            />
            <OptionSelectField
              label="Stream results"
              value={snapshots.streamResults}
              options={ON_OFF}
              onChange={(streamResults) => update("expireSnapshots", { streamResults })}
            />
          </>
        }
      />

      <OperationPolicySection
        title="Remove orphan files"
        included={orphans.included}
        onIncludedChange={(included) => include("removeOrphanFiles", included)}
        target={
          <WholeNumberField
            label="Older than (seconds)"
            unit="seconds"
            hint="Files no snapshot references, older than this; at least 1 day"
            value={orphans.olderThan}
            onChange={(olderThan) => update("removeOrphanFiles", { olderThan })}
          />
        }
        options={
          <>
            <WholeNumberField
              label="Max concurrent deletes"
              value={orphans.maxConcurrentDeletes}
              onChange={(maxConcurrentDeletes) => update("removeOrphanFiles", { maxConcurrentDeletes })}
            />
            <OptionSelectField
              label="Prefix mismatch mode"
              value={orphans.prefixMismatchMode}
              options={PREFIX_MISMATCH_MODES}
              onChange={(prefixMismatchMode) => update("removeOrphanFiles", { prefixMismatchMode })}
            />
          </>
        }
      />
    </FormDialog>
  );
}
