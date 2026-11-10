import { cva } from "class-variance-authority";
import { createContext, forwardRef, useContext, type ComponentProps, type ReactNode } from "react";
import { cn } from "../../lib/cn";

// An open history of events: a thin line down the left joins one marker per entry, with no box
// and no row borders. A nested timeline (the entries a folded line discloses) has neither line nor
// markers and reads in the quiet style.
const NestedContext = createContext(false);

export type TimelineProps = ComponentProps<"ul"> & {
  nested?: boolean;
};

export const Timeline = forwardRef<HTMLUListElement, TimelineProps>(({ nested = false, className, ...rest }, ref) => (
  <NestedContext.Provider value={nested}>
    <ul
      ref={ref}
      className={cn(
        "relative flex min-w-0 flex-col",
        nested
          ? "pl-12"
          : "before:absolute before:top-4 before:bottom-4 before:left-3.5 before:w-px before:-translate-x-1/2 before:bg-outline",
        className,
      )}
      {...rest}
    />
  </NestedContext.Provider>
));
Timeline.displayName = "Timeline";

export type TimelineMarker = "filled" | "outlined" | "dashed";

// filled: the entry started something, in the theme colour as an active state. outlined: any other
// entry. dashed: a folded stretch of quiet entries.
const markerStyle = cva("relative size-3 shrink-0 rounded-full border-2", {
  variants: {
    marker: {
      filled: "border-primary bg-primary",
      outlined: "border-outline-dim bg-surface",
      dashed: "border-dashed border-outline-dim bg-surface",
    },
  },
});

export type TimelineItemProps = Omit<ComponentProps<"li">, "title" | "onSelect" | "aria-expanded" | "aria-controls"> & {
  marker?: TimelineMarker;
  title: ReactNode;
  description?: ReactNode;
  // Beside the entry, outside its button, so it can be a link or another control of its own.
  trailingAction?: ReactNode;
  onSelect?: () => void;
  // Passed to the entry's button, for an entry that discloses more entries (its children).
  "aria-expanded"?: boolean;
  "aria-controls"?: string;
};

export const TimelineItem = forwardRef<HTMLLIElement, TimelineItemProps>(
  (
    {
      marker = "outlined",
      title,
      description,
      trailingAction,
      onSelect,
      "aria-expanded": ariaExpanded,
      "aria-controls": ariaControls,
      className,
      children,
      ...rest
    },
    ref,
  ) => {
    const nested = useContext(NestedContext);
    const quiet = nested || marker === "dashed";
    const titleType = quiet ? "type-body-small" : "type-label-large";
    const contentStyle = cn(
      "flex min-h-row min-w-0 flex-1 flex-col justify-center rounded-sm px-2 text-left",
      quiet ? "py-1 text-on-surface-variant" : "py-2 text-on-surface",
    );
    const content = (
      <>
        <span className={cn(titleType, "break-words")}>{title}</span>
        {description && <span className="type-body-small text-on-surface-variant">{description}</span>}
      </>
    );
    return (
      <li ref={ref} className={cn("relative min-w-0", className)} {...rest}>
        <div className="flex min-w-0 items-start">
          {!nested && (
            <span
              aria-hidden="true"
              data-marker={marker}
              className={cn(titleType, "flex h-lh w-7 shrink-0 items-center justify-center", quiet ? "mt-1" : "mt-2")}
            >
              <span className={markerStyle({ marker })} />
            </span>
          )}
          {onSelect ? (
            <button
              type="button"
              onClick={onSelect}
              aria-expanded={ariaExpanded}
              aria-controls={ariaControls}
              className={cn(
                contentStyle,
                "cursor-pointer hover:bg-hovered-variant focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-focus-ring",
                quiet && "hover:text-on-surface",
              )}
            >
              {content}
            </button>
          ) : (
            <div className={contentStyle}>{content}</div>
          )}
          {trailingAction !== undefined && (
            <span className="type-body-small shrink-0 self-center px-3">{trailingAction}</span>
          )}
        </div>
        {children}
      </li>
    );
  },
);
TimelineItem.displayName = "TimelineItem";
