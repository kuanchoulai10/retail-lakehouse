import { forwardRef, type ComponentProps } from "react";
import { cn } from "../../lib/cn";

export type BadgeProps = ComponentProps<"span">;

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, ...rest }, ref) => (
    <span
      ref={ref}
      className={cn(
        "type-label-medium inline-flex min-h-6 items-center rounded-xl px-2",
        "bg-surface-container-dim text-on-surface",
        className,
      )}
      {...rest}
    />
  ),
);
Badge.displayName = "Badge";
