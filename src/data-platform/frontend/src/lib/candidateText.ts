import type { CompactionCandidateApiResponse } from "@/api/generated/model";

// Why a compaction candidate is not in a run yet, in words. A compaction round grants the best
// pending candidates across tables within its budget, at most N (partitions per run) per table;
// the table's next run takes the granted ones.

const HOLD_REASON_TEXT: Record<string, string> = {
  too_small: "Too small to be worth compacting",
  recently_written: "Still being written; checked again after a quiet period",
  not_due: "Compaction is not due on this table",
};

const ROUND_ID_PREFIX = "compaction-rounds-";

// A scheduled round is named by its workflow id, the schedule's id and the time it fired; the
// time alone names it.
export function shortRoundId(roundId: string): string {
  return roundId.startsWith(ROUND_ID_PREFIX) ? roundId.slice(ROUND_ID_PREFIX.length) : roundId;
}

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
        ? `Waiting for a later round: below the top ${partitionsPerRun} (${partitionsPerRun} per run)`
        : "Waiting for the next round";
    case "granted":
      return candidate.granted_round_id === null
        ? "Granted"
        : `Granted in round ${shortRoundId(candidate.granted_round_id)}`;
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
