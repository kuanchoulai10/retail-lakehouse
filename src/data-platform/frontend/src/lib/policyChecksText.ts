import type { MaintenanceTriggersApiRequest } from "@/api/generated/model";
import { formatSeconds } from "@/format";
import { DEFAULT_DEBOUNCE_SECONDS } from "./policyDraft";

// When a policy checks its tables, in words: "Every 1 h, and 5 min after a commit".
export function policyChecksText(on: MaintenanceTriggersApiRequest): string {
  const every = `Every ${formatSeconds(on.schedule.every_seconds)}`;
  const commit = on.catalog_commit ?? null;
  if (commit === null) return every;
  const debounce = commit.debounce_seconds ?? DEFAULT_DEBOUNCE_SECONDS;
  return debounce === 0 ? `${every}, and right after a commit` : `${every}, and ${formatSeconds(debounce)} after a commit`;
}
