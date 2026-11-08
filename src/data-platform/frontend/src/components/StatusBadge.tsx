import { StatusBadge as StatusPill } from "@retail-lakehouse/design-system";
import { statusTone } from "@/lib/statusTone";

interface Props {
  status: string;
}

export function StatusBadge({ status }: Props) {
  const lower = status.toLowerCase();
  return <StatusPill status={statusTone(lower)}>{lower.charAt(0).toUpperCase() + lower.slice(1)}</StatusPill>;
}
