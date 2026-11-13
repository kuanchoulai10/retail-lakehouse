import type { CompactionCandidateApiResponse } from "@/api/generated/model";
import { formatSeconds, formatTimestamp } from "@/format";

// Why a compaction candidate is not in a run yet, in words. A compaction round grants the best
// pending candidates across tables within its budget, at most N (partitions per run) per table;
// the table's next run takes the granted ones.

const HOLD_REASON_TEXT: Record<string, string> = {
  too_small: "Too small to be worth compacting",
  recently_written: "Still being written; checked again after a quiet period",
  not_due: "Compaction is not due on this table",
  cooldown: "Compaction is cooling down on this table; its wait for a round goes on",
};

function words(key: string): string {
  return key.replaceAll("_", " ");
}

// The rounds page with this round open.
export function roundPath(roundId: string): string {
  return `/compaction-rounds?${new URLSearchParams({ round: roundId }).toString()}`;
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
        ? `Waiting for a later round: below the top ${partitionsPerRun} (${partitionsPerRun} per table per round)`
        : "Waiting for the next round";
    case "granted":
      // A round is named by when it started, as the rounds list shows it.
      return candidate.granted_round_started_at === null
        ? "Granted"
        : `Granted in round ${formatTimestamp(candidate.granted_round_started_at)}`;
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

const WAIT_UNITS: [number, string][] = [
  [86_400, "d"],
  [3_600, "h"],
  [60, "min"],
];

// A wait in its largest whole unit: "45 min", "3 h", "3 d".
function waitText(seconds: number): string {
  for (const [size, unit] of WAIT_UNITS) {
    if (seconds >= size) return `${Math.floor(seconds / size)} ${unit}`;
  }
  return `${Math.max(0, Math.floor(seconds))} s`;
}

// Why a candidate is overdue: it has waited, pending, longer than its priority's SLA allows.
export function overdueText(
  candidate: Pick<CompactionCandidateApiResponse, "priority" | "pending_since">,
  slaSeconds: number | undefined,
  now: Date = new Date(),
): string {
  const { priority, pending_since: since } = candidate;
  if (since === null) {
    return slaSeconds === undefined
      ? `Waited longer than ${priority} allows`
      : `Waited longer than ${priority} allows (${formatSeconds(slaSeconds)})`;
  }
  const waited = waitText((now.getTime() - new Date(since).getTime()) / 1000);
  return slaSeconds === undefined
    ? `Waited ${waited}, longer than ${priority} allows`
    : `Waited ${waited}; ${priority} allows ${formatSeconds(slaSeconds)}`;
}
