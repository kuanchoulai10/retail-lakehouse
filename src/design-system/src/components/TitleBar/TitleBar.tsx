import { useId, type ReactNode } from "react";
import { IconDots } from "../../icons";
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
  disabled?: boolean;
  /** Shown under the label and announced as the item's description, e.g. why it is disabled. */
  description?: string;
};

export type TitleBarProps = {
  breadcrumbs?: ReactNode;
  title: ReactNode;
  actions?: ReactNode;
  overflowActions?: TitleBarOverflowAction[];
};

function OverflowItem({ action }: { action: TitleBarOverflowAction }) {
  const id = useId();
  const labelId = `${id}-label`;
  const descriptionId = `${id}-description`;
  return (
    <DropdownMenuItem
      onSelect={action.onSelect}
      disabled={action.disabled}
      aria-labelledby={action.description ? labelId : undefined}
      aria-describedby={action.description ? descriptionId : undefined}
      className={action.destructive ? "text-negative-text" : undefined}
    >
      {action.description ? (
        <span className="flex flex-col">
          <span id={labelId}>{action.label}</span>
          <span id={descriptionId} className="type-body-small">
            {action.description}
          </span>
        </span>
      ) : (
        action.label
      )}
    </DropdownMenuItem>
  );
}

export function TitleBar({ breadcrumbs, title, actions, overflowActions }: TitleBarProps) {
  const collapses = Boolean(overflowActions?.length);
  return (
    <div className="flex flex-col gap-2 pb-4">
      {breadcrumbs}
      <div className="flex items-start justify-between gap-3">
        <h1
          title={typeof title === "string" ? title : undefined}
          className="type-headline-small min-w-0 flex-1 text-on-surface [overflow-wrap:anywhere] md:truncate"
        >
          {title}
        </h1>
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
                  icon={<IconDots />}
                />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {overflowActions?.map((action) => (
                  <OverflowItem key={action.label} action={action} />
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}
      </div>
    </div>
  );
}
