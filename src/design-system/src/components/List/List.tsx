import { forwardRef, type ComponentProps, type ReactNode } from "react";
import { cn } from "../../lib/cn";

export const List = forwardRef<HTMLUListElement, ComponentProps<"ul">>(
  ({ className, ...rest }, ref) => (
    <ul ref={ref} className={cn("flex flex-col", className)} {...rest} />
  ),
);
List.displayName = "List";

export type ListItemProps = Omit<ComponentProps<"li">, "title" | "onSelect"> & {
  title: ReactNode;
  description?: ReactNode;
  leadingIcon?: ReactNode;
  trailingItem?: ReactNode;
  isSelected?: boolean;
  onSelect?: () => void;
};

export const ListItem = forwardRef<HTMLLIElement, ListItemProps>(
  (
    { title, description, leadingIcon, trailingItem, isSelected = false, onSelect, className, ...rest },
    ref,
  ) => {
    const rowStyle = cn(
      "flex min-h-row w-full items-center gap-3 px-3 py-1 text-left text-on-surface",
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
          <span className="type-label-large">{title}</span>
          {description && (
            <span className={cn("type-body-small", isSelected ? "text-on-surface" : "text-on-surface-variant")}>
              {description}
            </span>
          )}
        </span>
        {trailingItem && <span className="shrink-0">{trailingItem}</span>}
      </>
    );
    return (
      <li ref={ref} className={className} {...rest}>
        {onSelect ? (
          <button
            type="button"
            onClick={onSelect}
            aria-current={isSelected ? "true" : undefined}
            className={cn(
              rowStyle,
              "cursor-pointer hover:bg-hovered-variant focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-focus-ring",
            )}
          >
            {content}
          </button>
        ) : (
          <div className={rowStyle}>{content}</div>
        )}
      </li>
    );
  },
);
ListItem.displayName = "ListItem";
