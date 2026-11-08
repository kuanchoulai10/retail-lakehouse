import { Tabs as TabsPrimitive } from "radix-ui";
import { forwardRef, type ComponentProps } from "react";
import { cn } from "../../lib/cn";

export const Tabs = TabsPrimitive.Root;

export const TabList = forwardRef<HTMLDivElement, ComponentProps<typeof TabsPrimitive.List>>(
  ({ className, ...rest }, ref) => (
    <TabsPrimitive.List
      ref={ref}
      className={cn("flex overflow-x-auto shadow-[inset_0_-1px_0_var(--color-outline-dim)]", className)}
      {...rest}
    />
  ),
);
TabList.displayName = "TabList";

export const TabItem = forwardRef<HTMLButtonElement, ComponentProps<typeof TabsPrimitive.Trigger>>(
  ({ className, ...rest }, ref) => (
    <TabsPrimitive.Trigger
      ref={ref}
      className={cn(
        "type-label-large min-h-control shrink-0 cursor-pointer border-b-2 border-transparent px-4 whitespace-nowrap text-on-surface-variant",
        "hover:bg-on-surface/5 data-[state=active]:border-primary data-[state=active]:text-on-surface",
        "focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-focus-ring",
        className,
      )}
      {...rest}
    />
  ),
);
TabItem.displayName = "TabItem";

export const TabPanel = forwardRef<HTMLDivElement, ComponentProps<typeof TabsPrimitive.Content>>(
  ({ className, ...rest }, ref) => (
    <TabsPrimitive.Content
      ref={ref}
      className={cn(
        "type-body-large py-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus-ring",
        className,
      )}
      {...rest}
    />
  ),
);
TabPanel.displayName = "TabPanel";
