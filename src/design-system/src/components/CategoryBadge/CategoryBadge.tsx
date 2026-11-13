import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type ComponentProps } from "react";
import { cn } from "../../lib/cn";

const categoryBadgeStyle = cva(
  "type-label-medium inline-flex min-h-6 items-center rounded-xl px-2",
  {
    variants: {
      category: {
        accent: "bg-inverse-primary text-on-surface",
        neutral: "bg-surface-container-dim text-on-surface",
        muted: "bg-surface-container text-on-surface-variant italic! line-through",
      },
    },
  },
);

export type CategoryBadgeProps = ComponentProps<"span"> &
  Required<VariantProps<typeof categoryBadgeStyle>>;

export const CategoryBadge = forwardRef<HTMLSpanElement, CategoryBadgeProps>(
  ({ category, className, ...rest }, ref) => (
    <span ref={ref} className={cn(categoryBadgeStyle({ category }), className)} {...rest} />
  ),
);
CategoryBadge.displayName = "CategoryBadge";
