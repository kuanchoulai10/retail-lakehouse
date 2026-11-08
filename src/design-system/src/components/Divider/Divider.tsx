import { Separator } from "radix-ui";
import { forwardRef, type ComponentProps } from "react";
import { cn } from "../../lib/cn";

export type DividerProps = ComponentProps<typeof Separator.Root>;

export const Divider = forwardRef<HTMLDivElement, DividerProps>(
  ({ orientation = "horizontal", className, ...rest }, ref) => (
    <Separator.Root
      ref={ref}
      orientation={orientation}
      className={cn(
        "shrink-0 bg-outline-dim",
        orientation === "horizontal" ? "h-px w-full" : "min-h-2.5 w-px self-stretch",
        className,
      )}
      {...rest}
    />
  ),
);
Divider.displayName = "Divider";
