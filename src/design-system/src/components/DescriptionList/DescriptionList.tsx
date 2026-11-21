import type { ReactNode } from "react";
import { cn } from "../../lib/cn";

export type DescriptionListItem = {
  term: string;
  description: ReactNode;
  id?: string;
};

export type DescriptionListProps = {
  items: DescriptionListItem[];
  className?: string;
};

export function DescriptionList({ items, className }: DescriptionListProps) {
  return (
    <dl
      className={cn(
        "grid grid-cols-1 gap-x-4 gap-y-1",
        "md:grid-cols-[minmax(0,max-content)_minmax(0,1fr)] md:gap-y-2",
        className,
      )}
    >
      {items.map((item) => (
        <div key={item.id ?? item.term} className="contents">
          <dt className="type-label-medium text-on-surface-variant">{item.term}</dt>
          <dd className="type-body-medium min-w-0 break-words text-on-surface max-md:mb-2">
            {item.description}
          </dd>
        </div>
      ))}
    </dl>
  );
}
