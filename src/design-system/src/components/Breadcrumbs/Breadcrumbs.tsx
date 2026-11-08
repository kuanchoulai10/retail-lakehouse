import { Slot } from "radix-ui";
import type { ReactNode } from "react";
import { SerendieSymbolChevronRight } from "../../icons";

export type BreadcrumbItem = { label: string; href?: string };

export type BreadcrumbsProps = {
  items: BreadcrumbItem[];
  renderLink: (item: BreadcrumbItem, children: ReactNode) => ReactNode;
};

export function Breadcrumbs({ items, renderLink }: BreadcrumbsProps) {
  return (
    <nav aria-label="Breadcrumb">
      <ol className="type-body-medium flex flex-wrap items-center gap-x-1 gap-y-0.5 text-on-surface-variant">
        {items.map((item, index) => {
          const isLast = index === items.length - 1;
          const label = (
            <span title={item.label} className="block max-w-[24ch] truncate">
              {item.label}
            </span>
          );
          return (
            <li key={`${index}-${item.label}`} className="flex min-w-0 items-center gap-1">
              {isLast || !item.href ? (
                <span
                  aria-current={isLast ? "page" : undefined}
                  className={isLast ? "min-w-0 text-on-surface" : "min-w-0"}
                >
                  {label}
                </span>
              ) : (
                <Slot.Root className="min-w-0 rounded-sm px-1 text-primary hover:bg-hovered-variant focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus-ring">
                  {renderLink(item, label)}
                </Slot.Root>
              )}
              {!isLast && (
                <SerendieSymbolChevronRight aria-hidden="true" className="size-4 shrink-0" />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
