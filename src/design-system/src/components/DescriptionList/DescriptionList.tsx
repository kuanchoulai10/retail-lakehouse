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
        "grid grid-cols-1 md:grid-cols-[minmax(0,max-content)_minmax(0,1fr)] md:gap-x-4 md:gap-y-2",
        className,
      )}
    >
      {items.map((item) => (
        <div
          key={item.id ?? item.term}
          className="max-md:flex max-md:flex-col max-md:gap-1 max-md:not-last:mb-2 md:contents"
        >
          <dt className="type-label-medium text-on-surface-variant">{item.term}</dt>
          <dd className="type-body-medium min-w-0 break-words text-on-surface">
            {item.description}
          </dd>
        </div>
      ))}
    </dl>
  );
}
