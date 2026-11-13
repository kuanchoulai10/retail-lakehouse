import type { CompactionRoundApiResponse } from "@/api/generated/model";
import { tablePath } from "@/lib/catalogPaths";

// What a compaction round's record says, in words: why a candidate was skipped, how much of the
// budget the picks use, and where a pick's table lives in the console.

const SKIP_REASON_TEXT: Record<string, string> = {
  budget_used: "Budget used",
  table_share_used: "Table's share used",
};

export function skipReasonText(reason: string): string {
  return SKIP_REASON_TEXT[reason] ?? reason.replaceAll("_", " ");
}

// "0.04 of 0.05 (80%)": the first pick is always taken, so a round can use more than its budget.
export function usedText(round: Pick<CompactionRoundApiResponse, "used_gb_hours" | "budget_gb_hours">): string {
  const used = round.used_gb_hours.toFixed(2);
  if (round.budget_gb_hours <= 0) return used;
  const percent = Math.round((round.used_gb_hours / round.budget_gb_hours) * 100);
  return `${used} of ${round.budget_gb_hours.toFixed(2)} (${percent}%)`;
}

// A round names a table "catalog.namespace.table", with the namespace levels joined by "." as
// maintenance stores them; the Candidates tab of that table, or null for a table no longer known.
export function candidatesPathOf(tableName: string | null): string | null {
  if (tableName === null) return null;
  const parts = tableName.split(".");
  if (parts.length < 3) return null;
  return tablePath(parts[0]!, parts.slice(1, -1), parts.at(-1)!, "candidates");
}
