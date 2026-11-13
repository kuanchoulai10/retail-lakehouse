import { priorityText } from "@/lib/priorityText";
import { useSchedulerPriorities } from "@/lib/useSchedulerPriorities";

// A maintenance priority with its SLA, "P2 (within 8 h)", wherever a priority is shown.
export function PriorityText({ priority }: { priority: string }) {
  const priorities = useSchedulerPriorities();
  return <span className="whitespace-nowrap">{priorityText(priority, priorities)}</span>;
}
