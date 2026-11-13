import type { CompactionCandidateApiResponse } from "@/api/generated/model";

// Why a compaction candidate is not in the next run, in words. A pending candidate in the top N
// (N partitions per run) has nothing against it, so it reads "".

const HOLD_REASON_TEXT: Record<string, string> = {
  too_small: "Too small to be worth compacting",
  recently_written: "Still being written; checked again after a quiet period",
};

function words(key: string): string {
  return key.replaceAll("_", " ");
}

export function whyNotPicked(candidate: CompactionCandidateApiResponse, partitionsPerRun: number): string {
  switch (candidate.state) {
    case "held": {
      const reason = candidate.hold_reason;
      if (reason === null) return "Held";
      return HOLD_REASON_TEXT[reason] ?? `Held: ${words(reason)}`;
    }
    case "pending":
      return candidate.rank !== null && candidate.rank > partitionsPerRun
        ? `Score below the top ${partitionsPerRun} (${partitionsPerRun} per run)`
        : "";
    case "claimed":
    case "running":
      return candidate.claimed_by_run_id === null ? "In a run" : `In run ${candidate.claimed_by_run_id}`;
    case "done":
    case "failed":
      return "Waiting for the next observation";
    default:
      return "";
  }
}
