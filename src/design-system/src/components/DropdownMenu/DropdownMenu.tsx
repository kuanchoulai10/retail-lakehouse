import { DropdownMenu as MenuPrimitive } from "radix-ui";
import { forwardRef, type ComponentProps } from "react";
import { IconCheck } from "../../icons";
import { cn } from "../../lib/cn";

export const DropdownMenu = MenuPrimitive.Root;
export const DropdownMenuTrigger = MenuPrimitive.Trigger;
export const DropdownMenuRadioGroup = MenuPrimitive.RadioGroup;

const itemStyle = [
  "type-body-large relative flex min-h-row cursor-pointer items-center rounded-sm py-1 pr-3 pl-3 outline-none select-none",
  "data-[highlighted]:bg-hovered-variant data-[highlighted]:outline-2 data-[highlighted]:-outline-offset-2",
  "data-[highlighted]:outline-focus-ring data-[disabled]:cursor-not-allowed data-[disabled]:text-on-disabled",
];

export const DropdownMenuContent = forwardRef<
  HTMLDivElement,
  ComponentProps<typeof MenuPrimitive.Content>
>(({ className, sideOffset = 4, align = "start", ...rest }, ref) => (
  <MenuPrimitive.Portal>
    <MenuPrimitive.Content
      ref={ref}
      sideOffset={sideOffset}
      align={align}
      className={cn(
        "z-50 min-w-48 rounded-md border border-outline-dim bg-surface-container-bright p-1 text-on-surface shadow-lg",
        className,
      )}
      {...rest}
    />
  </MenuPrimitive.Portal>
));
DropdownMenuContent.displayName = "DropdownMenuContent";

export const DropdownMenuItem = forwardRef<
  HTMLDivElement,
  ComponentProps<typeof MenuPrimitive.Item>
>(({ className, ...rest }, ref) => (
  <MenuPrimitive.Item ref={ref} className={cn(itemStyle, className)} {...rest} />
));
DropdownMenuItem.displayName = "DropdownMenuItem";

export const DropdownMenuRadioItem = forwardRef<
  HTMLDivElement,
  ComponentProps<typeof MenuPrimitive.RadioItem>
>(({ className, children, ...rest }, ref) => (
  <MenuPrimitive.RadioItem ref={ref} className={cn(itemStyle, "pl-9", className)} {...rest}>
    <MenuPrimitive.ItemIndicator className="absolute left-2">
      <IconCheck aria-hidden="true" className="size-5" />
    </MenuPrimitive.ItemIndicator>
    {children}
  </MenuPrimitive.RadioItem>
));
DropdownMenuRadioItem.displayName = "DropdownMenuRadioItem";

export const DropdownMenuSeparator = forwardRef<
  HTMLDivElement,
  ComponentProps<typeof MenuPrimitive.Separator>
>(({ className, ...rest }, ref) => (
  <MenuPrimitive.Separator ref={ref} className={cn("my-1 h-px bg-outline-dim", className)} {...rest} />
));
DropdownMenuSeparator.displayName = "DropdownMenuSeparator";
