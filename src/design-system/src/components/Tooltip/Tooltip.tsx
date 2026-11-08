import { Tooltip as TooltipPrimitive } from "radix-ui";
import type { ComponentProps, ReactNode } from "react";
import { cn } from "../../lib/cn";

export const TooltipProvider = TooltipPrimitive.Provider;

export type TooltipProps = {
  content: ReactNode;
  children: ReactNode;
  side?: ComponentProps<typeof TooltipPrimitive.Content>["side"];
  className?: string;
};

export function Tooltip({ content, children, side = "top", className }: TooltipProps) {
  return (
    <TooltipPrimitive.Root>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          side={side}
          sideOffset={6}
          className={cn(
            "type-body-small z-50 max-w-50 rounded-sm bg-on-surface px-2 py-1 text-surface",
            className,
          )}
        >
          {content}
          <TooltipPrimitive.Arrow className="fill-on-surface" />
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}
