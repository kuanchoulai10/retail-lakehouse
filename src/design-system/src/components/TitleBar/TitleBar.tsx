import type { ReactNode } from "react";
import { SerendieSymbolMoreHorizontal } from "../../icons";
import { cn } from "../../lib/cn";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../DropdownMenu/DropdownMenu";
import { IconButton } from "../IconButton/IconButton";

export type TitleBarOverflowAction = {
  label: string;
  onSelect: () => void;
  destructive?: boolean;
};

export type TitleBarProps = {
  breadcrumbs?: ReactNode;
  title: ReactNode;
  actions?: ReactNode;
  overflowActions?: TitleBarOverflowAction[];
};

export function TitleBar({ breadcrumbs, title, actions, overflowActions }: TitleBarProps) {
  const collapses = Boolean(overflowActions?.length);
  return (
    <div className="flex flex-col gap-2 pb-4">
      {breadcrumbs}
      <div className="flex items-start justify-between gap-3">
        <h1 className="type-headline-small min-w-0 flex-1 break-words text-on-surface">{title}</h1>
        {actions && (
          <div
            className={cn(
              "shrink-0 items-center gap-2",
              collapses ? "hidden md:flex" : "flex flex-wrap justify-end",
            )}
          >
            {actions}
          </div>
        )}
        {collapses && (
          <div className="shrink-0 md:hidden">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <IconButton
                  aria-label="More actions"
                  styleType="ghost"
                  icon={<SerendieSymbolMoreHorizontal />}
                />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {overflowActions?.map((action) => (
                  <DropdownMenuItem
                    key={action.label}
                    onSelect={action.onSelect}
                    className={action.destructive ? "text-negative-text" : undefined}
                  >
                    {action.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}
      </div>
    </div>
  );
}
