import { Badge } from "@/components/ui/badge";

interface Props {
  status: string;
}

export function StatusBadge({ status }: Props) {
  const lower = status.toLowerCase();
  return (
    <Badge variant="outline" className="text-muted-foreground">
      {lower.charAt(0).toUpperCase() + lower.slice(1)}
    </Badge>
  );
}
