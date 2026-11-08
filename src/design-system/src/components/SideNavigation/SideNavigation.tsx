import { Slot } from "radix-ui";
import type { ReactNode } from "react";
import type { IconComponent } from "../../icons";
import { cn } from "../../lib/cn";

export type SideNavigationItem = {
  href: string;
  label: string;
  icon: IconComponent;
  isActive: boolean;
};

export type SideNavigationProps = {
  items: SideNavigationItem[];
  renderLink: (item: SideNavigationItem, children: ReactNode) => ReactNode;
  onNavigate?: () => void;
};

export function SideNavigation({ items, renderLink, onNavigate }: SideNavigationProps) {
  return (
    <nav aria-label="Main" className="p-2">
      <ul className="flex flex-col gap-1">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <li key={item.href}>
              <Slot.Root
                aria-current={item.isActive ? "page" : undefined}
                onClick={onNavigate}
                className={cn(
                  "type-label-large flex min-h-control items-center gap-3 rounded-md px-3",
                  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus-ring",
                  item.isActive
                    ? "bg-selected-surface text-on-surface [&_svg]:text-primary"
                    : "text-on-surface hover:bg-hovered-variant",
                )}
              >
                {renderLink(
                  item,
                  <>
                    <Icon aria-hidden="true" className="size-6 shrink-0" />
                    <span className="min-w-0 truncate">{item.label}</span>
                  </>,
                )}
              </Slot.Root>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
