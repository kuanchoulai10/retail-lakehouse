import { Panel } from "@retail-lakehouse/design-system";
import type { ReactNode } from "react";
import type { OperationPoliciesApiRequest } from "@/api/generated/model";
import { formatBytes, formatCount, formatSeconds } from "@/format";

interface Fact {
  label: string;
  value: ReactNode;
}

function Facts({ facts }: { facts: Fact[] }) {
  return (
    <dl className="grid grid-cols-1 gap-x-4 gap-y-1 sm:grid-cols-[12rem_1fr] sm:gap-y-2">
      {facts.map((fact) => (
        <div key={fact.label} className="contents">
          <dt className="text-on-surface-variant">{fact.label}</dt>
          <dd className="tabular-nums">{fact.value}</dd>
        </div>
      ))}
    </dl>
  );
}

// Conditions combine with OR; with none, the operation is due once its cooldown has passed.
function conditions(texts: (string | null)[]): string {
  const set = texts.filter((text): text is string => text !== null);
  return set.length === 0 ? "None: due once the cooldown has passed" : set.join(", or ");
}

function seconds(value: number): string {
  return `${formatCount(value)} s (${formatSeconds(value)})`;
}

function bytes(value: number | null | undefined, unset: string): string {
  return value === null || value === undefined ? unset : formatBytes(value);
}

function Operation({ title, enabled, facts }: { title: string; enabled: boolean; facts: Fact[] }) {
  return (
    <Panel title={title}>
      <Facts facts={enabled ? [{ label: "Enabled", value: "On" }, ...facts] : [{ label: "Enabled", value: "Off" }]} />
    </Panel>
  );
}

interface Props {
  description: string;
  reconcileIntervalSeconds: number;
  dryRun: boolean;
  operations: OperationPoliciesApiRequest;
}

// A policy's content to read, not edit: the editor's fields as plain facts, one panel per
// operation. An operation that is off shows only that.
export function PolicySummary({ description, reconcileIntervalSeconds, dryRun, operations }: Props) {
  const { rewrite_data_files: data, rewrite_manifests: manifests, expire_snapshots: snapshots, remove_orphan_files: orphans } =
    operations;
  const smallManifests = manifests.trigger_policy.conditions.small_manifests;
  const reducible = data.trigger_policy.conditions.reducible_files;
  const expirable = snapshots.trigger_policy.conditions.expirable_snapshots;
  return (
    <div className="type-body-medium flex flex-col gap-6">
      <Panel title="Policy">
        <Facts
          facts={[
            { label: "Description", value: description === "" ? "—" : description },
            { label: "Reconcile interval", value: seconds(reconcileIntervalSeconds) },
            { label: "Dry run", value: dryRun ? "On: nothing is started" : "Off" },
          ]}
        />
      </Panel>
      <Operation
        title="Rewrite data files"
        enabled={data.enabled}
        facts={[
          { label: "Scope", value: data.scope.unit === "table" ? "Whole table" : "Each partition" },
          { label: "Cooldown", value: seconds(data.trigger_policy.cooldown_seconds) },
          {
            label: "Conditions",
            value: conditions([reducible ? `Reducible files at least ${formatCount(reducible.at_least)}` : null]),
          },
          { label: "Target file size", value: bytes(data.execution_policy.target_file_size_bytes, "The table's own") },
          { label: "Min input files", value: formatCount(data.execution_policy.min_input_files) },
          {
            label: "Partial progress",
            value: data.execution_policy.partial_progress.enabled
              ? `On${
                  data.execution_policy.partial_progress.max_commits == null
                    ? ""
                    : `, at most ${formatCount(data.execution_policy.partial_progress.max_commits)} commits`
                }`
              : "Off",
          },
        ]}
      />
      <Operation
        title="Rewrite manifests"
        enabled={manifests.enabled}
        facts={[
          { label: "Cooldown", value: seconds(manifests.trigger_policy.cooldown_seconds) },
          {
            label: "Conditions",
            value: conditions([
              smallManifests
                ? `Small manifests at least ${formatCount(smallManifests.at_least)}${
                    smallManifests.smaller_than_bytes == null ? "" : `, smaller than ${formatBytes(smallManifests.smaller_than_bytes)}`
                  }`
                : null,
            ]),
          },
        ]}
      />
      <Operation
        title="Expire snapshots"
        enabled={snapshots.enabled}
        facts={[
          { label: "Cooldown", value: seconds(snapshots.trigger_policy.cooldown_seconds) },
          {
            label: "Conditions",
            value: conditions([expirable ? `Expirable snapshots at least ${formatCount(expirable.at_least)}` : null]),
          },
          { label: "Older than", value: seconds(snapshots.execution_policy.older_than_seconds) },
          { label: "Retain last", value: formatCount(snapshots.execution_policy.retain_last) },
        ]}
      />
      <Operation
        title="Remove orphan files"
        enabled={orphans.enabled}
        facts={[
          { label: "Cooldown", value: seconds(orphans.trigger_policy.cooldown_seconds) },
          { label: "Conditions", value: conditions([]) },
          { label: "Older than", value: seconds(orphans.execution_policy.older_than_seconds) },
        ]}
      />
    </div>
  );
}
