import { StatusBadge as StatusPill } from "@retail-lakehouse/design-system";
import { sentenceCase } from "@/lib/sentenceCase";
import { statusTone } from "@/lib/statusTone";

interface Props {
  status: string;
}

export function StatusBadge({ status }: Props) {
  const lower = status.toLowerCase();
  return <StatusPill status={statusTone(lower)}>{sentenceCase(lower)}</StatusPill>;
}
