import { forwardRef, type ComponentProps, type ReactNode } from "react";
import { cn } from "../../lib/cn";

export type EmptyStateProps = Omit<ComponentProps<"div">, "title"> & {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
};

export const EmptyState = forwardRef<HTMLDivElement, EmptyStateProps>(
  ({ title, description, action, className, ...rest }, ref) => (
    <div
      ref={ref}
      className={cn("flex flex-col items-center gap-2 px-4 py-8 text-center", className)}
      {...rest}
    >
      <p className="type-title-medium text-on-surface">{title}</p>
      {description ? (
        <p className="type-body-medium max-w-prose text-on-surface-variant">{description}</p>
      ) : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  ),
);
EmptyState.displayName = "EmptyState";
