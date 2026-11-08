import { Slot } from "radix-ui";
import { forwardRef, type ComponentProps } from "react";
import { cn } from "../../lib/cn";

export type TextLinkProps = ComponentProps<"a"> & {
  asChild?: boolean;
  inline?: boolean;
};

export const TextLink = forwardRef<HTMLAnchorElement, TextLinkProps>(
  ({ asChild = false, inline = false, className, ...rest }, ref) => {
    const Comp = asChild ? Slot.Root : "a";
    return (
      <Comp
        ref={ref}
        className={cn(
          "rounded-sm text-primary underline-offset-2",
          inline ? "underline" : "hover:underline",
          "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus-ring",
          className,
        )}
        {...rest}
      />
    );
  },
);
TextLink.displayName = "TextLink";
