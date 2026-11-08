import { StatusBadge } from "@/components/StatusBadge";

interface Props {
  status: string;
}

// A maintenance run or operation state; the tone mapping is shared with every status badge.
export function RunStatusBadge({ status }: Props) {
  return <StatusBadge status={status} />;
}
