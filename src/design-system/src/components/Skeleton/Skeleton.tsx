import { forwardRef, type ComponentProps } from "react";
import { cn } from "../../lib/cn";

export type SkeletonProps = Omit<ComponentProps<"div">, "children">;

export const Skeleton = forwardRef<HTMLDivElement, SkeletonProps>(
  ({ className, ...rest }, ref) => (
    <div
      ref={ref}
      aria-hidden="true"
      className={cn(
        "animate-pulse rounded-md bg-surface-container-dim motion-reduce:animate-none",
        className,
      )}
      {...rest}
    />
  ),
);
Skeleton.displayName = "Skeleton";
