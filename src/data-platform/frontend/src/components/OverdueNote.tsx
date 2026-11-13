import type { CompactionCandidateApiResponse } from "@/api/generated/model";
import { StatusBadge } from "@/components/StatusBadge";
import { overdueText } from "@/lib/candidateText";
import { useSchedulerPriorities } from "@/lib/useSchedulerPriorities";

// The Overdue badge with why: how long the candidate has waited and how long its priority allows.
// Overdue is the one mark on the Candidates tab that calls for attention, a sign the round budget
// is too small.
export function OverdueNote({ candidate }: { candidate: CompactionCandidateApiResponse }) {
  const priorities = useSchedulerPriorities();
  const sla = priorities?.find((p) => p.priority === candidate.priority)?.sla_seconds;
  return (
    <>
      <StatusBadge status="overdue" />
      <span className="type-body-small text-on-surface-variant">{overdueText(candidate, sla)}</span>
    </>
  );
}
