import type {
  CompactionScopeApiRequestUnit,
  CreateTableMaintenancePolicyApiRequest,
} from "@/api/generated/model";

// Everything a policy write carries except its name: the API takes it whole, always.
export type PolicyContent = Omit<CreateTableMaintenancePolicyApiRequest, "name">;

// A policy as the editor holds it. Numbers stay text until submit, so an empty optional
// value (a condition not checked, a value left to the table) is kept apart from a zero.
export interface PolicyDraft {
  description: string;
  reconcileInterval: string;
  dryRun: boolean;
  rewriteDataFiles: {
    enabled: boolean;
    scope: CompactionScopeApiRequestUnit;
    cooldown: string;
    reducibleFiles: string;
    targetFileSizeBytes: string;
    minInputFiles: string;
    partialProgress: boolean;
    maxCommits: string;
  };
  rewriteManifests: {
    enabled: boolean;
    cooldown: string;
    smallManifests: string;
    smallerThanBytes: string;
  };
  expireSnapshots: {
    enabled: boolean;
    cooldown: string;
    expirableSnapshots: string;
    olderThan: string;
    retainLast: string;
  };
  removeOrphanFiles: {
    enabled: boolean;
    cooldown: string;
    olderThan: string;
  };
}

export const POLICY_NAME_PATTERN = /^[A-Za-z0-9_-]{1,64}$/;

function text(value: number | null | undefined): string {
  return value === null || value === undefined ? "" : String(value);
}

export function draftFromContent(content: PolicyContent): PolicyDraft {
  const { rewrite_data_files: data, rewrite_manifests: manifests, expire_snapshots: snapshots, remove_orphan_files: orphans } =
    content.operations;
  return {
    description: content.description,
    reconcileInterval: text(content.reconcile_interval_seconds),
    dryRun: content.dry_run,
    rewriteDataFiles: {
      enabled: data.enabled,
      scope: data.scope.unit,
      cooldown: text(data.trigger_policy.cooldown_seconds),
      reducibleFiles: text(data.trigger_policy.conditions.reducible_files?.at_least),
      targetFileSizeBytes: text(data.execution_policy.target_file_size_bytes),
      minInputFiles: text(data.execution_policy.min_input_files),
      partialProgress: data.execution_policy.partial_progress.enabled,
      maxCommits: text(data.execution_policy.partial_progress.max_commits),
    },
    rewriteManifests: {
      enabled: manifests.enabled,
      cooldown: text(manifests.trigger_policy.cooldown_seconds),
      smallManifests: text(manifests.trigger_policy.conditions.small_manifests?.at_least),
      smallerThanBytes: text(manifests.trigger_policy.conditions.small_manifests?.smaller_than_bytes),
    },
    expireSnapshots: {
      enabled: snapshots.enabled,
      cooldown: text(snapshots.trigger_policy.cooldown_seconds),
      expirableSnapshots: text(snapshots.trigger_policy.conditions.expirable_snapshots?.at_least),
      olderThan: text(snapshots.execution_policy.older_than_seconds),
      retainLast: text(snapshots.execution_policy.retain_last),
    },
    removeOrphanFiles: {
      enabled: orphans.enabled,
      cooldown: text(orphans.trigger_policy.cooldown_seconds),
      olderThan: text(orphans.execution_policy.older_than_seconds),
    },
  };
}

class InvalidDraft extends Error {}

// Reads one field; `where` and `label` name it in the message the editor shows.
function whole(value: string, label: string, where?: string): number {
  const trimmed = value.trim();
  if (!/^\d+$/.test(trimmed)) {
    throw new InvalidDraft(`${where === undefined ? "" : `${where}: `}${label} must be a whole number.`);
  }
  return Number(trimmed);
}

function positive(value: string, label: string): number {
  const number = whole(value, label);
  if (number === 0) throw new InvalidDraft(`${label} must be greater than zero.`);
  return number;
}

function optionalWhole(value: string, label: string, where: string): number | null {
  return value.trim() === "" ? null : whole(value, label, where);
}

function atLeast(value: string, label: string, where: string): { at_least: number } | null {
  const number = optionalWhole(value, label, where);
  return number === null ? null : { at_least: number };
}

function smallManifests(draft: PolicyDraft["rewriteManifests"]) {
  const where = "Rewrite manifests";
  const at = optionalWhole(draft.smallManifests, "Small manifests at least", where);
  const smallerThan = optionalWhole(draft.smallerThanBytes, "Smaller than (bytes)", where);
  if (at === null && smallerThan !== null) {
    throw new InvalidDraft(`${where}: set Small manifests at least to use Smaller than.`);
  }
  return at === null ? null : { at_least: at, smaller_than_bytes: smallerThan };
}

function buildContent(draft: PolicyDraft): PolicyContent {
  const { rewriteDataFiles: data, rewriteManifests: manifests, expireSnapshots: snapshots, removeOrphanFiles: orphans } =
    draft;
  return {
    description: draft.description.trim(),
    reconcile_interval_seconds: positive(draft.reconcileInterval, "Reconcile interval"),
    dry_run: draft.dryRun,
    operations: {
      rewrite_data_files: {
        enabled: data.enabled,
        scope: { unit: data.scope },
        trigger_policy: {
          cooldown_seconds: whole(data.cooldown, "Cooldown", "Rewrite data files"),
          conditions: { reducible_files: atLeast(data.reducibleFiles, "Reducible files at least", "Rewrite data files") },
        },
        execution_policy: {
          target_file_size_bytes: optionalWhole(data.targetFileSizeBytes, "Target file size", "Rewrite data files"),
          min_input_files: whole(data.minInputFiles, "Min input files", "Rewrite data files"),
          partial_progress: {
            enabled: data.partialProgress,
            max_commits: optionalWhole(data.maxCommits, "Max commits", "Rewrite data files"),
          },
        },
      },
      rewrite_manifests: {
        enabled: manifests.enabled,
        trigger_policy: {
          cooldown_seconds: whole(manifests.cooldown, "Cooldown", "Rewrite manifests"),
          conditions: { small_manifests: smallManifests(manifests) },
        },
        execution_policy: {},
      },
      expire_snapshots: {
        enabled: snapshots.enabled,
        trigger_policy: {
          cooldown_seconds: whole(snapshots.cooldown, "Cooldown", "Expire snapshots"),
          conditions: {
            expirable_snapshots: atLeast(snapshots.expirableSnapshots, "Expirable snapshots at least", "Expire snapshots"),
          },
        },
        execution_policy: {
          older_than_seconds: whole(snapshots.olderThan, "Older than", "Expire snapshots"),
          retain_last: whole(snapshots.retainLast, "Retain last", "Expire snapshots"),
        },
      },
      remove_orphan_files: {
        enabled: orphans.enabled,
        trigger_policy: { cooldown_seconds: whole(orphans.cooldown, "Cooldown", "Remove orphan files"), conditions: {} },
        execution_policy: { older_than_seconds: whole(orphans.olderThan, "Older than", "Remove orphan files") },
      },
    },
  };
}

// The content to send, or the first field that cannot be sent, named for the user.
export function contentFromDraft(draft: PolicyDraft): { content: PolicyContent } | { error: string } {
  try {
    return { content: buildContent(draft) };
  } catch (failure) {
    if (failure instanceof InvalidDraft) return { error: failure.message };
    throw failure;
  }
}
