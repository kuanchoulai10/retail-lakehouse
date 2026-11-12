import { Slot } from "radix-ui";
import type { ReactNode } from "react";
import type { IconComponent } from "../../icons";
import { cn } from "../../lib/cn";
import { Tooltip, TooltipProvider } from "../Tooltip/Tooltip";

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
  isCollapsed?: boolean;
};

export function SideNavigation({ items, renderLink, onNavigate, isCollapsed = false }: SideNavigationProps) {
  return (
    <TooltipProvider>
      <nav aria-label="Main" className="p-2">
        <ul className="flex flex-col gap-1">
          {items.map((item) => {
            const Icon = item.icon;
            const link = (
              <Slot.Root
                aria-current={item.isActive ? "page" : undefined}
                onClick={onNavigate}
                className={cn(
                  "type-label-large flex min-h-control items-center gap-3 rounded-md",
                  isCollapsed ? "justify-center px-0" : "px-3",
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
                    {/* The label's line height is 1, so the padding keeps descenders inside the truncating box. */}
                    <span className={cn("min-w-0 truncate py-0.5", isCollapsed && "sr-only")}>
                      {item.label}
                    </span>
                  </>,
                )}
              </Slot.Root>
            );
            return (
              <li key={item.href}>
                {isCollapsed ? (
                  <Tooltip content={item.label} side="right">
                    {link}
                  </Tooltip>
                ) : (
                  link
                )}
              </li>
            );
          })}
        </ul>
      </nav>
    </TooltipProvider>
  );
}
