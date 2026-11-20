import { priorityText } from "@/lib/priorityText";

// A maintenance priority, "P2", wherever a priority is shown.
export function PriorityText({ priority }: { priority: string }) {
  return <span className="whitespace-nowrap">{priorityText(priority)}</span>;
}
