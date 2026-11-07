import { Skeleton } from "@/components/ui/skeleton";

interface Props {
  label: string;
}

export function PanelSkeleton({ label }: Props) {
  return (
    <div
      role="status"
      aria-busy="true"
      className="grid gap-2 rounded-lg border border-border bg-background p-4"
    >
      <span className="sr-only">{label}</span>
      <Skeleton className="h-4 w-1/3" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-2/3" />
    </div>
  );
}
