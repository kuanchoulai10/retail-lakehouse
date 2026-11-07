import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface Props {
  status: string;
}

function colourOf(status: string): string {
  if (status === "failed") return "text-destructive";
  if (status === "succeeded") return "text-success";
  return "text-muted-foreground";
}

export function RunStatusBadge({ status }: Props) {
  const lower = status.toLowerCase();
  return (
    <Badge variant="outline" className={cn(colourOf(lower))}>
      {lower.charAt(0).toUpperCase() + lower.slice(1)}
    </Badge>
  );
}
