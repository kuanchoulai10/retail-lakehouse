// What a maintenance attempt's record says, in words: why it failed, whether its Spark event log
// finished and what the platform did next.

const FAILURE_CLASS_TEXT: Record<string, string> = {
  oom: "Out of memory",
  timeout: "Timed out",
  commit_conflict: "Conflicted with another commit",
  permanent: "Retrying cannot fix it",
  cancelled: "Cancelled",
  other: "Other error",
};

const NEXT_STEP_TEXT: Record<string, string> = {
  done: "Done",
  retry_same: "Retrying at the same size",
  needs_attention: "Stopped: needs attention",
  attempts_used: "Stopped: no attempts left",
  not_retried: "Stopped: retrying will not help",
  cancelled: "Stopped: cancelled",
  still_running: "Stopped: its job is still running",
};

function sentenceCase(key: string): string {
  const words = key.replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

// "" for an attempt that has not failed (yet).
export function failureClassText(failureClass: string | null): string {
  if (failureClass === null) return "";
  return FAILURE_CLASS_TEXT[failureClass] ?? sentenceCase(failureClass);
}

// "" for an attempt still running, which has no next step yet.
export function nextStepText(step: string | null, nextSize: string | null): string {
  if (step === null) return "";
  if (step === "retry_larger") return nextSize === null ? "Retrying at a larger size" : `Retrying at size ${nextSize}`;
  return NEXT_STEP_TEXT[step] ?? sentenceCase(step);
}

export function eventLogText(finished: boolean | null): string {
  if (finished === null) return "Unknown";
  return finished ? "Finished" : "Did not finish";
}
