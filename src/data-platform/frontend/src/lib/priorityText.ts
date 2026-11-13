import type { SchedulerPriorityApiResponse } from "@/api/generated/model";
import { formatSeconds } from "@/format";

// A priority with the time the scheduler allows it, "P2 (within 8 h)": a pending partition waiting
// longer than that is overdue. Before the scheduler settings load, the priority alone.
export function priorityText(priority: string, priorities: SchedulerPriorityApiResponse[] | undefined): string {
  const setting = priorities?.find((p) => p.priority === priority);
  return setting === undefined ? priority : `${priority} (within ${formatSeconds(setting.sla_seconds)})`;
}

// How a round weights each priority's score, "P0 × 4, P1 × 2, P2 × 1".
export function priorityWeightsText(priorities: SchedulerPriorityApiResponse[]): string {
  return priorities.map((p) => `${p.priority} × ${p.weight}`).join(", ");
}
