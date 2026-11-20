import type {
  CreateTableMaintenancePolicyApiRequest,
  ExpireSnapshotsSpecApiRequest,
  RemoveOrphanFilesOptionsApiRequest,
  RemoveOrphanFilesSpecApiRequest,
  RewriteDataFilesOptionsApiRequest,
  RewriteDataFilesSpecApiRequest,
  RewriteDataFilesTargetApiRequestPer,
  RewriteManifestsSpecApiRequest,
} from "@/api/generated/model";

// Everything a policy write carries except its name: the API takes it whole, always.
export type PolicyContent = Omit<CreateTableMaintenancePolicyApiRequest, "name">;

// An option the procedure decides when it is empty: "" is "Procedure default".
export type OptionalBoolean = "" | "true" | "false";
export type RewriteStrategy = "" | "binpack" | "sort";
export type PrefixMismatchMode = "" | "ERROR" | "IGNORE" | "DELETE";

// A policy as the editor holds it. Numbers stay text until submit, so an empty optional value
// (an option left to the procedure, a retention left to the table) is kept apart from a zero.
// An operation taken out of the policy keeps its values, so putting it back brings them back.
export interface PolicyDraft {
  description: string;
  scheduleEvery: string;
  catalogCommit: boolean;
  debounce: string;
  dryRun: boolean;
  rewriteDataFiles: {
    included: boolean;
    reducibleFilesAtMost: string;
    per: RewriteDataFilesTargetApiRequestPer;
    strategy: RewriteStrategy;
    sortOrder: string;
    minInputFiles: string;
    partialProgressEnabled: OptionalBoolean;
    partialProgressMaxCommits: string;
    maxConcurrentFileGroupRewrites: string;
    rewriteAll: OptionalBoolean;
    deleteFileThreshold: string;
    removeDanglingDeletes: OptionalBoolean;
    maxFileGroupSizeBytes: string;
  };
  rewriteManifests: {
    included: boolean;
    smallManifestsAtMost: string;
    useCaching: OptionalBoolean;
  };
  expireSnapshots: {
    included: boolean;
    minSnapshotsToKeep: string;
    maxSnapshotAge: string;
    maxConcurrentDeletes: string;
    streamResults: OptionalBoolean;
  };
  removeOrphanFiles: {
    included: boolean;
    olderThan: string;
    maxConcurrentDeletes: string;
    prefixMismatchMode: PrefixMismatchMode;
  };
}

export const POLICY_NAME_PATTERN = /^[A-Za-z0-9_-]{1,64}$/;

// What the API applies when a policy names catalog commits without a debounce.
export const DEFAULT_DEBOUNCE_SECONDS = 300;
const SCHEDULE_SECONDS = { min: 60, max: 604_800 };
const DEBOUNCE_SECONDS = { min: 0, max: 86_400 };

function text(value: number | string | null | undefined): string {
  return value === null || value === undefined ? "" : String(value);
}

function booleanText(value: boolean | null | undefined): OptionalBoolean {
  if (value === null || value === undefined) return "";
  return value ? "true" : "false";
}

export function draftFromContent(content: PolicyContent): PolicyDraft {
  const data = content.rewrite_data_files ?? null;
  const manifests = content.rewrite_manifests ?? null;
  const snapshots = content.expire_snapshots ?? null;
  const orphans = content.remove_orphan_files ?? null;
  const dataOptions = data?.options ?? {};
  const commit = content.on.catalog_commit ?? null;
  return {
    description: content.description,
    scheduleEvery: text(content.on.schedule.every_seconds),
    catalogCommit: commit !== null,
    debounce: text(commit === null ? DEFAULT_DEBOUNCE_SECONDS : (commit.debounce_seconds ?? DEFAULT_DEBOUNCE_SECONDS)),
    dryRun: content.dry_run ?? false,
    rewriteDataFiles: {
      included: data !== null,
      reducibleFilesAtMost: text(data?.target.reducible_files.at_most),
      per: data?.target.per ?? "partition",
      strategy: dataOptions.strategy ?? "",
      sortOrder: dataOptions.sort_order ?? "",
      minInputFiles: text(dataOptions.min_input_files),
      partialProgressEnabled: booleanText(dataOptions.partial_progress_enabled),
      partialProgressMaxCommits: text(dataOptions.partial_progress_max_commits),
      maxConcurrentFileGroupRewrites: text(dataOptions.max_concurrent_file_group_rewrites),
      rewriteAll: booleanText(dataOptions.rewrite_all),
      deleteFileThreshold: text(dataOptions.delete_file_threshold),
      removeDanglingDeletes: booleanText(dataOptions.remove_dangling_deletes),
      maxFileGroupSizeBytes: text(dataOptions.max_file_group_size_bytes),
    },
    rewriteManifests: {
      included: manifests !== null,
      smallManifestsAtMost: text(manifests?.target.small_manifests.at_most),
      useCaching: booleanText(manifests?.options?.use_caching),
    },
    expireSnapshots: {
      included: snapshots !== null,
      minSnapshotsToKeep: text(snapshots?.target.min_snapshots_to_keep),
      maxSnapshotAge: text(snapshots?.target.max_snapshot_age_seconds),
      maxConcurrentDeletes: text(snapshots?.options?.max_concurrent_deletes),
      streamResults: booleanText(snapshots?.options?.stream_results),
    },
    removeOrphanFiles: {
      included: orphans !== null,
      olderThan: text(orphans?.target.older_than_seconds),
      maxConcurrentDeletes: text(orphans?.options?.max_concurrent_deletes),
      prefixMismatchMode: orphans?.options?.prefix_mismatch_mode ?? "",
    },
  };
}

export type OperationKey = "rewriteDataFiles" | "rewriteManifests" | "expireSnapshots" | "removeOrphanFiles";

// The target fields of each operation; all empty means the loaded policy did not hold it.
const TARGET_FIELDS = {
  rewriteDataFiles: ["reducibleFilesAtMost"],
  rewriteManifests: ["smallManifestsAtMost"],
  expireSnapshots: ["minSnapshotsToKeep", "maxSnapshotAge"],
  removeOrphanFiles: ["olderThan"],
} as const satisfies { [K in OperationKey]: readonly (keyof PolicyDraft[K])[] };

// Puts an operation into the policy. One with no target yet (the loaded policy left it out) is
// seeded from the platform default's target and options, filling only the fields that are empty;
// without a default, or with a target, the operation keeps what it holds.
export function includeOperation(draft: PolicyDraft, key: OperationKey, defaults: PolicyDraft | null): PolicyDraft {
  const current = draft[key] as unknown as Record<string, unknown>;
  const targetless = TARGET_FIELDS[key].every((field) => current[field] === "");
  const seed = defaults === null || !targetless ? {} : (defaults[key] as unknown as Record<string, unknown>);
  const filled = Object.fromEntries(
    Object.entries(current).map(([field, value]) => [field, value === "" && field in seed ? seed[field] : value]),
  );
  return { ...draft, [key]: { ...filled, included: true } };
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

function secondsWithin(value: string, label: string, range: { min: number; max: number }): number {
  const number = whole(value, label);
  if (number < range.min || number > range.max) {
    throw new InvalidDraft(`${label} must be ${range.min} to ${range.max} seconds.`);
  }
  return number;
}

function optionalWhole(value: string, label: string, where: string): number | null {
  return value.trim() === "" ? null : whole(value, label, where);
}

function optionalBoolean(value: OptionalBoolean): boolean | null {
  return value === "" ? null : value === "true";
}

// The options that are set, or null when none is: the API leaves every other one to the procedure.
function setOptions<Options extends object>(options: { [K in keyof Options]: Options[K] | null }): Options | null {
  const set = Object.fromEntries(Object.entries(options).filter(([, value]) => value !== null));
  return Object.keys(set).length === 0 ? null : (set as Options);
}

function rewriteDataFiles(draft: PolicyDraft["rewriteDataFiles"]): RewriteDataFilesSpecApiRequest {
  const where = "Rewrite data files";
  const sortOrder = draft.sortOrder.trim();
  return {
    target: {
      reducible_files: { at_most: whole(draft.reducibleFilesAtMost, "Reducible files at most", where) },
      per: draft.per,
    },
    options: setOptions<RewriteDataFilesOptionsApiRequest>({
      strategy: draft.strategy === "" ? null : draft.strategy,
      sort_order: sortOrder === "" ? null : sortOrder,
      min_input_files: optionalWhole(draft.minInputFiles, "Min input files", where),
      partial_progress_enabled: optionalBoolean(draft.partialProgressEnabled),
      partial_progress_max_commits: optionalWhole(draft.partialProgressMaxCommits, "Partial progress max commits", where),
      max_concurrent_file_group_rewrites: optionalWhole(
        draft.maxConcurrentFileGroupRewrites,
        "Max concurrent file group rewrites",
        where,
      ),
      rewrite_all: optionalBoolean(draft.rewriteAll),
      delete_file_threshold: optionalWhole(draft.deleteFileThreshold, "Delete file threshold", where),
      remove_dangling_deletes: optionalBoolean(draft.removeDanglingDeletes),
      max_file_group_size_bytes: optionalWhole(draft.maxFileGroupSizeBytes, "Max file group size", where),
    }),
  };
}

function rewriteManifests(draft: PolicyDraft["rewriteManifests"]): RewriteManifestsSpecApiRequest {
  return {
    target: { small_manifests: { at_most: whole(draft.smallManifestsAtMost, "Small manifests at most", "Rewrite manifests") } },
    options: setOptions({ use_caching: optionalBoolean(draft.useCaching) }),
  };
}

function expireSnapshots(draft: PolicyDraft["expireSnapshots"]): ExpireSnapshotsSpecApiRequest {
  const where = "Expire snapshots";
  return {
    // An empty retention value is sent as null: the table's property, else Iceberg's default, applies.
    target: {
      min_snapshots_to_keep: optionalWhole(draft.minSnapshotsToKeep, "Min snapshots to keep", where),
      max_snapshot_age_seconds: optionalWhole(draft.maxSnapshotAge, "Max snapshot age", where),
    },
    options: setOptions({
      max_concurrent_deletes: optionalWhole(draft.maxConcurrentDeletes, "Max concurrent deletes", where),
      stream_results: optionalBoolean(draft.streamResults),
    }),
  };
}

function removeOrphanFiles(draft: PolicyDraft["removeOrphanFiles"]): RemoveOrphanFilesSpecApiRequest {
  const where = "Remove orphan files";
  return {
    target: { older_than_seconds: whole(draft.olderThan, "Older than", where) },
    options: setOptions<RemoveOrphanFilesOptionsApiRequest>({
      max_concurrent_deletes: optionalWhole(draft.maxConcurrentDeletes, "Max concurrent deletes", where),
      prefix_mismatch_mode: draft.prefixMismatchMode === "" ? null : draft.prefixMismatchMode,
    }),
  };
}

// An operation out of the policy is sent as null, and its fields are not checked.
function block<Draft extends { included: boolean }, Spec>(draft: Draft, build: (draft: Draft) => Spec): Spec | null {
  return draft.included ? build(draft) : null;
}

function buildContent(draft: PolicyDraft): PolicyContent {
  return {
    description: draft.description.trim(),
    on: {
      schedule: { every_seconds: secondsWithin(draft.scheduleEvery, "Check every", SCHEDULE_SECONDS) },
      catalog_commit: draft.catalogCommit
        ? { debounce_seconds: secondsWithin(draft.debounce, "Debounce", DEBOUNCE_SECONDS) }
        : null,
    },
    dry_run: draft.dryRun,
    rewrite_data_files: block(draft.rewriteDataFiles, rewriteDataFiles),
    rewrite_manifests: block(draft.rewriteManifests, rewriteManifests),
    expire_snapshots: block(draft.expireSnapshots, expireSnapshots),
    remove_orphan_files: block(draft.removeOrphanFiles, removeOrphanFiles),
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
