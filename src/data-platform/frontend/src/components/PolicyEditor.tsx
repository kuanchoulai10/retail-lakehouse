import { Button, Switch, TextField } from "@retail-lakehouse/design-system";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  createTableMaintenancePolicy,
  getGetTableMaintenancePolicyQueryKey,
  getListTableMaintenancePoliciesQueryKey,
  getTableMaintenancePolicy,
  updateTableMaintenancePolicy,
} from "@/api/generated/maintenance-policies/maintenance-policies";
import type { MaintenancePriorityApi, TableMaintenancePolicyApiResponse } from "@/api/generated/model";
import { errorMessage } from "@/format";
import { priorityText } from "@/lib/priorityText";
import {
  contentFromDraft,
  draftFromContent,
  POLICY_NAME_PATTERN,
  type PolicyContent,
  type PolicyDraft,
} from "@/lib/policyDraft";
import { isConflict } from "@/lib/updateErrorMessage";
import { CheckboxField } from "./forms/CheckboxField";
import { FormDialog } from "./forms/FormDialog";
import { SelectField, type SelectOption } from "./forms/SelectField";
import { OperationPolicySection } from "./OperationPolicySection";
import { WholeNumberField } from "./forms/WholeNumberField";

const CONFLICT_MESSAGE = "Someone else changed this policy. Reload to see their version.";
const NAME_MESSAGE = "A name uses letters, digits, - and _ only, at most 64 characters.";
const PRIORITIES: MaintenancePriorityApi[] = ["P0", "P1", "P2"];

interface Props {
  // The policy being edited, at the version `content` was read at; without one the editor
  // creates a policy.
  policy?: Pick<TableMaintenancePolicyApiResponse, "name" | "version">;
  // What the form starts from: the edited policy's content, or for a new policy the default
  // policy's, as the page passes it. The editor never makes values up.
  content: PolicyContent;
  onClose: () => void;
}

type Write =
  | { kind: "create"; name: string; content: PolicyContent }
  | { kind: "update"; name: string; version: number; content: PolicyContent };

export function PolicyEditor({ policy, content, onClose }: Props) {
  const queryClient = useQueryClient();
  // The version the edit started from; a refetch while the dialog is open must not move it
  // forward, or the save would overwrite a change made meanwhile. Reload moves it on purpose.
  const [loaded, setLoaded] = useState(() =>
    policy === undefined ? null : { name: policy.name, version: policy.version },
  );
  const [draft, setDraft] = useState<PolicyDraft>(() => draftFromContent(content));
  const priorityOptions: SelectOption<MaintenancePriorityApi>[] = PRIORITIES.map((value) => ({
    value,
    label: priorityText(value),
  }));
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
        label="Reconcile interval (seconds)"
        unit="seconds"
        hint="How often each table is checked"
        value={draft.reconcileInterval}
        onChange={(value) => update("reconcileInterval", value)}
      />
      <div className="flex flex-col gap-1">
        <Switch label="Dry run" checked={draft.dryRun} onCheckedChange={(dryRun) => update("dryRun", dryRun)} />
        <p className="type-body-small text-on-surface-variant">
          Reconcile and record what would run, but run nothing.
        </p>
      </div>
      <div className="flex flex-col gap-1">
        <SelectField
          label="Priority"
          value={draft.priority}
          options={priorityOptions}
          onChange={(priority) => update("priority", priority)}
        />
        <p className="type-body-small text-on-surface-variant">
          Compaction rounds are gone: this priority no longer orders maintenance. A table&apos;s own priority (on its
          Overview tab) does. KCL-91 removes this field.
        </p>
      </div>

      <OperationPolicySection
        title="Rewrite data files"
        enabled={data.enabled}
        onEnabledChange={(enabled) => update("rewriteDataFiles", { enabled })}
        scope={{ value: data.scope, onChange: (scope) => update("rewriteDataFiles", { scope }) }}
        cooldown={{
          label: "Cooldown (seconds)",
          unit: "seconds",
          value: data.cooldown,
          onChange: (cooldown) => update("rewriteDataFiles", { cooldown }),
        }}
        conditions={[
          {
            label: "Reducible files",
            fields: [
              {
                label: "Reducible files at least",
                hint: "Files compaction would remove, counted per partition or across the table by scope",
                value: data.reducibleFiles,
                onChange: (reducibleFiles) => update("rewriteDataFiles", { reducibleFiles }),
              },
            ],
          },
        ]}
      >
        <WholeNumberField
          label="Target file size (bytes)"
          unit="bytes"
          hint="Empty: the table's write.target-file-size-bytes, else 512 MiB"
          value={data.targetFileSizeBytes}
          onChange={(targetFileSizeBytes) => update("rewriteDataFiles", { targetFileSizeBytes })}
        />
        <WholeNumberField
          label="Min input files"
          value={data.minInputFiles}
          onChange={(minInputFiles) => update("rewriteDataFiles", { minInputFiles })}
        />
        <CheckboxField
          label="Partial progress"
          checked={data.partialProgress}
          onChange={(partialProgress) => update("rewriteDataFiles", { partialProgress })}
        />
        <WholeNumberField
          label="Max commits"
          hint="Empty: the procedure's default"
          value={data.maxCommits}
          onChange={(maxCommits) => update("rewriteDataFiles", { maxCommits })}
        />
      </OperationPolicySection>

      <OperationPolicySection
        title="Rewrite manifests"
        enabled={manifests.enabled}
        onEnabledChange={(enabled) => update("rewriteManifests", { enabled })}
        cooldown={{
          label: "Cooldown (seconds)",
          unit: "seconds",
          value: manifests.cooldown,
          onChange: (cooldown) => update("rewriteManifests", { cooldown }),
        }}
        conditions={[
          {
            label: "Small manifests",
            fields: [
              {
                label: "Small manifests at least",
                value: manifests.smallManifests,
                onChange: (smallManifests) => update("rewriteManifests", { smallManifests }),
              },
              {
                label: "Smaller than (bytes)",
                unit: "bytes",
                hint: "Empty: derived from the table's manifest target size",
                value: manifests.smallerThanBytes,
                onChange: (smallerThanBytes) => update("rewriteManifests", { smallerThanBytes }),
              },
            ],
          },
        ]}
      />

      <OperationPolicySection
        title="Expire snapshots"
        enabled={snapshots.enabled}
        onEnabledChange={(enabled) => update("expireSnapshots", { enabled })}
        cooldown={{
          label: "Cooldown (seconds)",
          unit: "seconds",
          value: snapshots.cooldown,
          onChange: (cooldown) => update("expireSnapshots", { cooldown }),
        }}
        conditions={[
          {
            label: "Expirable snapshots",
            fields: [
              {
                label: "Expirable snapshots at least",
                hint: "Snapshots older than Older than and outside Retain last, below",
                value: snapshots.expirableSnapshots,
                onChange: (expirableSnapshots) => update("expireSnapshots", { expirableSnapshots }),
              },
            ],
          },
        ]}
      >
        <WholeNumberField
          label="Older than (seconds)"
          unit="seconds"
          value={snapshots.olderThan}
          onChange={(olderThan) => update("expireSnapshots", { olderThan })}
        />
        <WholeNumberField
          label="Retain last"
          value={snapshots.retainLast}
          onChange={(retainLast) => update("expireSnapshots", { retainLast })}
        />
      </OperationPolicySection>

      <OperationPolicySection
        title="Remove orphan files"
        enabled={orphans.enabled}
        onEnabledChange={(enabled) => update("removeOrphanFiles", { enabled })}
        cooldown={{
          label: "Cooldown (seconds)",
          unit: "seconds",
          value: orphans.cooldown,
          onChange: (cooldown) => update("removeOrphanFiles", { cooldown }),
        }}
        conditions={[]}
      >
        <WholeNumberField
          label="Older than (seconds)"
          unit="seconds"
          value={orphans.olderThan}
          onChange={(olderThan) => update("removeOrphanFiles", { olderThan })}
        />
      </OperationPolicySection>
    </FormDialog>
  );
}
