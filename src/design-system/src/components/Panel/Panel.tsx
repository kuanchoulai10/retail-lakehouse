import { forwardRef, useId, type ComponentProps, type ReactNode } from "react";
import { cn } from "../../lib/cn";

export type PanelProps = Omit<ComponentProps<"section">, "title"> & {
  title?: ReactNode;
  actions?: ReactNode;
};

export const Panel = forwardRef<HTMLElement, PanelProps>(
  ({ title, actions, className, children, ...rest }, ref) => {
    const headingId = useId();
    return (
      <section
        ref={ref}
        {...(title ? { "aria-labelledby": headingId } : {})}
        className={cn(
          "rounded-lg border border-outline bg-surface-container p-4 text-on-surface",
          className,
        )}
        {...rest}
      >
        {title || actions ? (
          <header className="mb-3 flex flex-wrap items-center justify-between gap-2">
            {title ? (
              <h2 id={headingId} className="type-title-small">
                {title}
              </h2>
            ) : null}
            {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
          </header>
        ) : null}
        {children}
      </section>
    );
  },
);
Panel.displayName = "Panel";
