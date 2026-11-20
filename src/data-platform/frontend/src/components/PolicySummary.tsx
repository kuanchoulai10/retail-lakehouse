import { Panel } from "@retail-lakehouse/design-system";
import type { ReactNode } from "react";
import { formatBytes, formatCount, formatSeconds } from "@/format";
import { policyChecksText } from "@/lib/policyChecksText";
import type { PolicyContent } from "@/lib/policyDraft";

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

const RETENTION_UNSET: ReactNode = (
  <>
    The table&apos;s <span className="font-mono">history.expire.*</span> / Iceberg default
  </>
);

function onOff(value: boolean): string {
  return value ? "On" : "Off";
}

type OptionValue = string | number | boolean;
type Option = [label: string, value: OptionValue | null | undefined, unit?: "bytes"];

// The options a block sets, one line each, as "Min input files: 2" (a text value is an identifier
// or SQL, so it is set in mono; a size in bytes is read back as plain text); unset ones are the
// procedure's.
function Options({ options }: { options: Option[] }) {
  const set = options.filter((option): option is [string, OptionValue, "bytes"?] => option[1] != null);
  if (set.length === 0) return "Procedure defaults";
  return (
    <ul className="flex flex-col gap-1">
      {set.map(([label, value, unit]) => (
        <li key={label}>
          {label}:{" "}
          {typeof value === "boolean" ? (
            onOff(value)
          ) : typeof value === "number" ? (
            unit === "bytes" ? formatBytes(value) : formatCount(value)
          ) : (
            <span className="font-mono">{value}</span>
          )}
        </li>
      ))}
    </ul>
  );
}

// An operation the policy leaves out says only that; one it holds shows its target and options.
function Operation({ title, facts }: { title: string; facts: Fact[] | null }) {
  return (
    <Panel title={title}>
      {facts === null ? <p className="text-on-surface-variant">Not in this policy</p> : <Facts facts={facts} />}
    </Panel>
  );
}

// A policy's content to read, not edit: the editor's fields as plain facts, one panel per operation.
export function PolicySummary({ content }: { content: PolicyContent }) {
  const data = content.rewrite_data_files ?? null;
  const manifests = content.rewrite_manifests ?? null;
  const snapshots = content.expire_snapshots ?? null;
  const orphans = content.remove_orphan_files ?? null;
  return (
    <div className="type-body-medium flex flex-col gap-6">
      <Panel title="Policy">
        <Facts
          facts={[
            { label: "Description", value: content.description === "" ? "—" : content.description },
            { label: "Checks", value: policyChecksText(content.on) },
            {
              label: "Dry run",
              value: content.dry_run === true ? "On. Scheduled checks record what would run and start nothing; a manual run still runs." : "Off",
            },
          ]}
        />
      </Panel>
      <Operation
        title="Rewrite data files"
        facts={
          data === null
            ? null
            : [
                {
                  label: "Target",
                  value: `Reducible files at most ${formatCount(data.target.reducible_files.at_most)}, ${
                    data.target.per === "table" ? "across the table" : "per partition"
                  }`,
                },
                {
                  label: "Options",
                  value: (
                    <Options
                      options={[
                        ["Strategy", data.options?.strategy],
                        ["Sort order", data.options?.sort_order],
                        ["Min input files", data.options?.min_input_files],
                        ["Partial progress", data.options?.partial_progress_enabled],
                        ["Partial progress max commits", data.options?.partial_progress_max_commits],
                        ["Max concurrent file group rewrites", data.options?.max_concurrent_file_group_rewrites],
                        ["Rewrite all", data.options?.rewrite_all],
                        ["Delete file threshold", data.options?.delete_file_threshold],
                        ["Remove dangling deletes", data.options?.remove_dangling_deletes],
                        ["Max file group size", data.options?.max_file_group_size_bytes, "bytes"],
                      ]}
                    />
                  ),
                },
              ]
        }
      />
      <Operation
        title="Rewrite manifests"
        facts={
          manifests === null
            ? null
            : [
                { label: "Target", value: `Small manifests at most ${formatCount(manifests.target.small_manifests.at_most)}` },
                { label: "Options", value: <Options options={[["Use caching", manifests.options?.use_caching]]} /> },
              ]
        }
      />
      <Operation
        title="Expire snapshots"
        facts={
          snapshots === null
            ? null
            : [
                {
                  label: "Snapshots to keep",
                  value:
                    snapshots.target.min_snapshots_to_keep == null
                      ? RETENTION_UNSET
                      : `Keep at least ${formatCount(snapshots.target.min_snapshots_to_keep)} snapshots`,
                },
                {
                  label: "Snapshot age",
                  value:
                    snapshots.target.max_snapshot_age_seconds == null
                      ? RETENTION_UNSET
                      : `Expire snapshots older than ${formatSeconds(snapshots.target.max_snapshot_age_seconds)}`,
                },
                {
                  label: "Options",
                  value: (
                    <Options
                      options={[
                        ["Max concurrent deletes", snapshots.options?.max_concurrent_deletes],
                        ["Stream results", snapshots.options?.stream_results],
                      ]}
                    />
                  ),
                },
              ]
        }
      />
      <Operation
        title="Remove orphan files"
        facts={
          orphans === null
            ? null
            : [
                {
                  label: "Target",
                  value: `Remove orphan files older than ${formatSeconds(orphans.target.older_than_seconds)}`,
                },
                {
                  label: "Options",
                  value: (
                    <Options
                      options={[
                        ["Max concurrent deletes", orphans.options?.max_concurrent_deletes],
                        ["Prefix mismatch mode", orphans.options?.prefix_mismatch_mode],
                      ]}
                    />
                  ),
                },
              ]
        }
      />
    </div>
  );
}
