import { describe, expect, it } from "vitest";
import { policyContentFixture } from "@/test/fixtures";
import {
  contentFromDraft,
  draftFromContent,
  includeOperation,
  type PolicyContent,
  type PolicyDraft,
} from "./policyDraft";

function contentOf(draft: PolicyDraft): PolicyContent {
  const result = contentFromDraft(draft);
  if ("error" in result) throw new Error(result.error);
  return result.content;
}

function errorOf(draft: PolicyDraft): string {
  const result = contentFromDraft(draft);
  if (!("error" in result)) throw new Error("expected an error");
  return result.error;
}

describe("policyDraft", () => {
  it("round-trips the platform default content", () => {
    const content = policyContentFixture();
    expect(contentOf(draftFromContent(content))).toEqual(content);
  });

  it("holds every value as text, an unset option as empty", () => {
    const draft = draftFromContent(policyContentFixture());
    expect(draft.scheduleEvery).toBe("3600");
    expect(draft.catalogCommit).toBe(true);
    expect(draft.debounce).toBe("300");
    expect(draft.rewriteDataFiles).toMatchObject({
      included: true,
      reducibleFilesAtMost: "5",
      per: "partition",
      minInputFiles: "2",
      partialProgressEnabled: "true",
      rewriteAll: "",
      strategy: "",
    });
    expect(draft.removeOrphanFiles).toMatchObject({ included: true, olderThan: "259200", prefixMismatchMode: "" });
  });

  it("sends an excluded operation as null and reads it back as excluded", () => {
    const draft = draftFromContent(policyContentFixture());
    const excluded: PolicyDraft = { ...draft, expireSnapshots: { ...draft.expireSnapshots, included: false } };
    const content = contentOf(excluded);
    expect(content.expire_snapshots).toBeNull();
    // The draft keeps what the operation held, so switching it back on brings the values back
    // (PolicyEditor's keyboard test switches it off and on).
    expect(draftFromContent(content).expireSnapshots.included).toBe(false);
  });

  it("seeds an operation put into the policy with no target from the platform default", () => {
    const content: PolicyContent = policyContentFixture();
    delete content.remove_orphan_files;
    const draft = draftFromContent(content);
    const defaults = draftFromContent(policyContentFixture());
    const typed: PolicyDraft = {
      ...draft,
      removeOrphanFiles: { ...draft.removeOrphanFiles, prefixMismatchMode: "IGNORE" },
    };
    expect(includeOperation(typed, "removeOrphanFiles", defaults).removeOrphanFiles).toEqual({
      included: true,
      olderThan: "259200",
      maxConcurrentDeletes: "",
      prefixMismatchMode: "IGNORE",
    });
  });

  it("puts an operation with a target back as it was, without seeding", () => {
    const draft = draftFromContent(policyContentFixture());
    const excluded: PolicyDraft = {
      ...draft,
      expireSnapshots: { ...draft.expireSnapshots, included: false, minSnapshotsToKeep: "3", maxSnapshotAge: "" },
    };
    const defaults = draftFromContent(policyContentFixture());
    expect(includeOperation(excluded, "expireSnapshots", defaults).expireSnapshots).toEqual({
      ...excluded.expireSnapshots,
      included: true,
    });
  });

  it("puts an operation back without seeding when there is no default", () => {
    const content: PolicyContent = policyContentFixture();
    delete content.rewrite_manifests;
    const draft = draftFromContent(content);
    expect(includeOperation(draft, "rewriteManifests", null).rewriteManifests).toEqual({
      ...draft.rewriteManifests,
      included: true,
    });
  });

  it("reads an absent block as excluded", () => {
    const content: PolicyContent = policyContentFixture();
    delete content.rewrite_manifests;
    expect(draftFromContent(content).rewriteManifests.included).toBe(false);
  });

  it("does not check the fields of an excluded operation", () => {
    const draft = draftFromContent(policyContentFixture());
    const excluded: PolicyDraft = {
      ...draft,
      removeOrphanFiles: { ...draft.removeOrphanFiles, included: false, olderThan: "soon" },
    };
    expect(contentOf(excluded).remove_orphan_files).toBeNull();
  });

  it("sends catalog_commit as null when commits do not trigger a check", () => {
    const draft = { ...draftFromContent(policyContentFixture()), catalogCommit: false };
    expect(contentOf(draft).on).toEqual({ schedule: { every_seconds: 3600 }, catalog_commit: null });
  });

  it("leaves an empty option out, and sends options as null when none is set", () => {
    const draft = draftFromContent(policyContentFixture());
    const cleared: PolicyDraft = {
      ...draft,
      rewriteDataFiles: { ...draft.rewriteDataFiles, minInputFiles: " ", partialProgressEnabled: "" },
      removeOrphanFiles: { ...draft.removeOrphanFiles, maxConcurrentDeletes: "4" },
    };
    const content = contentOf(cleared);
    expect(content.rewrite_data_files?.options).toBeNull();
    expect(content.remove_orphan_files?.options).toEqual({ max_concurrent_deletes: 4 });
  });

  it("sends every option of rewrite data files it is given", () => {
    const draft = draftFromContent(policyContentFixture());
    const all: PolicyDraft = {
      ...draft,
      rewriteDataFiles: {
        ...draft.rewriteDataFiles,
        per: "table",
        strategy: "sort",
        sortOrder: "id DESC NULLS LAST",
        partialProgressMaxCommits: "10",
        maxConcurrentFileGroupRewrites: "5",
        rewriteAll: "false",
        deleteFileThreshold: "3",
        removeDanglingDeletes: "true",
        maxFileGroupSizeBytes: "1073741824",
      },
    };
    expect(contentOf(all).rewrite_data_files).toEqual({
      target: { reducible_files: { at_most: 5 }, per: "table" },
      options: {
        strategy: "sort",
        sort_order: "id DESC NULLS LAST",
        min_input_files: 2,
        partial_progress_enabled: true,
        partial_progress_max_commits: 10,
        max_concurrent_file_group_rewrites: 5,
        rewrite_all: false,
        delete_file_threshold: 3,
        remove_dangling_deletes: true,
        max_file_group_size_bytes: 1073741824,
      },
    });
  });

  it("sends a retention value left empty as null, left to the table", () => {
    const draft = draftFromContent(policyContentFixture());
    const unset: PolicyDraft = { ...draft, expireSnapshots: { ...draft.expireSnapshots, maxSnapshotAge: "" } };
    expect(contentOf(unset).expire_snapshots?.target).toEqual({
      min_snapshots_to_keep: 10,
      max_snapshot_age_seconds: null,
    });
  });

  it("refuses a check interval outside 60 to 604800 seconds", () => {
    const draft = draftFromContent(policyContentFixture());
    expect(errorOf({ ...draft, scheduleEvery: "30" })).toBe("Check every must be 60 to 604800 seconds.");
    expect(errorOf({ ...draft, scheduleEvery: "604801" })).toBe("Check every must be 60 to 604800 seconds.");
    expect(errorOf({ ...draft, scheduleEvery: "" })).toBe("Check every must be a whole number.");
  });

  it("refuses a debounce outside 0 to 86400 seconds only while commits trigger a check", () => {
    const draft = draftFromContent(policyContentFixture());
    expect(errorOf({ ...draft, debounce: "86401" })).toBe("Debounce must be 0 to 86400 seconds.");
    expect(contentOf({ ...draft, debounce: "86401", catalogCommit: false }).on.catalog_commit).toBeNull();
  });

  it("names the section and the field of a value that is not a whole number", () => {
    const draft = draftFromContent(policyContentFixture());
    expect(
      errorOf({ ...draft, expireSnapshots: { ...draft.expireSnapshots, minSnapshotsToKeep: "1e" } }),
    ).toBe("Expire snapshots: Min snapshots to keep must be a whole number.");
    expect(
      errorOf({ ...draft, rewriteDataFiles: { ...draft.rewriteDataFiles, reducibleFilesAtMost: "" } }),
    ).toBe("Rewrite data files: Reducible files at most must be a whole number.");
  });
});
