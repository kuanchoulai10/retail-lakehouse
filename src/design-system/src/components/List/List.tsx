import { forwardRef, type ComponentProps, type ReactNode } from "react";
import { cn } from "../../lib/cn";

export const List = forwardRef<HTMLUListElement, ComponentProps<"ul">>(
  ({ className, ...rest }, ref) => (
    <ul ref={ref} className={cn("flex flex-col", className)} {...rest} />
  ),
);
List.displayName = "List";

export type ListItemProps = Omit<ComponentProps<"li">, "title" | "onSelect" | "aria-expanded" | "aria-controls"> & {
  title: ReactNode;
  description?: ReactNode;
  leadingIcon?: ReactNode;
  trailingItem?: ReactNode;
  isSelected?: boolean;
  onSelect?: () => void;
  // Passed to the row's button, for a row that discloses more content.
  "aria-expanded"?: boolean;
  "aria-controls"?: string;
};

export const ListItem = forwardRef<HTMLLIElement, ListItemProps>(
  (
    {
      title,
      description,
      leadingIcon,
      trailingItem,
      isSelected = false,
      onSelect,
      "aria-expanded": ariaExpanded,
      "aria-controls": ariaControls,
      className,
      ...rest
    },
    ref,
  ) => {
    const rowStyle = cn(
      "flex min-h-row w-full min-w-0 items-center gap-3 px-3 py-1 text-left text-on-surface",
      isSelected && "bg-selected-surface",
    );
    const content = (
      <>
        {leadingIcon && (
          <span aria-hidden="true" className="shrink-0 [&_svg]:size-6">
            {leadingIcon}
          </span>
        )}
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="type-label-large break-words">{title}</span>
          {description && (
            <span className={cn("type-body-small", isSelected ? "text-on-surface" : "text-on-surface-variant")}>
              {description}
            </span>
          )}
        </span>
        {trailingItem && <span className="shrink-0">{trailingItem}</span>}
      </>
    );
    const row = onSelect ? (
      <button
        type="button"
        onClick={onSelect}
        aria-current={isSelected ? "true" : undefined}
        aria-expanded={ariaExpanded}
        aria-controls={ariaControls}
        className={cn(
          rowStyle,
          "cursor-pointer hover:bg-hovered-variant focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-focus-ring",
        )}
      >
        {content}
      </button>
    ) : (
      <div className={rowStyle}>{content}</div>
    );
    return (
      <li ref={ref} className={className} {...rest}>
        {row}
      </li>
    );
  },
);
ListItem.displayName = "ListItem";
