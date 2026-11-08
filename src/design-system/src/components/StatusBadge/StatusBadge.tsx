import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type ComponentProps } from "react";
import { cn } from "../../lib/cn";

const statusBadgeStyle = cva(
  "type-label-medium inline-flex min-h-6 items-center rounded-xl px-2",
  {
    variants: {
      status: {
        positive: "bg-positive-container text-on-positive-container",
        notice: "bg-notice-container text-on-notice-container",
        negative: "bg-negative-container text-on-negative-container",
        neutral: "bg-surface-container-dim text-on-surface",
      },
    },
  },
);

export type StatusBadgeProps = ComponentProps<"span"> &
  Required<VariantProps<typeof statusBadgeStyle>>;

export const StatusBadge = forwardRef<HTMLSpanElement, StatusBadgeProps>(
  ({ status, className, ...rest }, ref) => (
    <span ref={ref} className={cn(statusBadgeStyle({ status }), className)} {...rest} />
  ),
);
StatusBadge.displayName = "StatusBadge";
