import { Select as SelectPrimitive } from "radix-ui";
import { forwardRef, type ComponentProps } from "react";
import { cn } from "../../lib/cn";
import { FieldFrame, fieldControlStyle, type FieldProps } from "../../lib/Field";
import { IconCheck, IconChevronDown } from "../../icons";

export type SelectItem = { value: string; label: string };

export type SelectProps = FieldProps &
  Pick<
    ComponentProps<typeof SelectPrimitive.Root>,
    "value" | "defaultValue" | "onValueChange" | "disabled" | "name"
  > & {
    items: SelectItem[];
    placeholder?: string;
    id?: string;
    className?: string;
  };

export const Select = forwardRef<HTMLButtonElement, SelectProps>(
  (
    {
      label,
      description,
      invalid,
      invalidMessage,
      required,
      hideLabel,
      id,
      items,
      placeholder,
      className,
      ...rootProps
    },
    ref,
  ) => (
    <FieldFrame {...{ label, description, invalid, invalidMessage, required, hideLabel, id }}>
      {({ required: isRequired, ...controlProps }) => (
        <SelectPrimitive.Root required={isRequired} {...rootProps}>
          <SelectPrimitive.Trigger
            ref={ref}
            className={cn(
              fieldControlStyle,
              "flex h-control cursor-pointer items-center justify-between gap-2 text-left",
              "data-[placeholder]:text-on-surface-variant",
              className,
            )}
            {...controlProps}
          >
            <SelectPrimitive.Value placeholder={placeholder} />
            <SelectPrimitive.Icon asChild>
              <IconChevronDown aria-hidden="true" className="size-6 shrink-0" />
            </SelectPrimitive.Icon>
          </SelectPrimitive.Trigger>
          <SelectPrimitive.Portal>
            <SelectPrimitive.Content
              position="popper"
              sideOffset={4}
              className={cn(
                "z-50 max-h-(--radix-select-content-available-height) min-w-(--radix-select-trigger-width)",
                "overflow-hidden rounded-md border border-outline-dim bg-surface-container-bright text-on-surface shadow-lg",
              )}
            >
              <SelectPrimitive.Viewport className="p-1">
                {items.map((item) => (
                  <SelectPrimitive.Item
                    key={item.value}
                    value={item.value}
                    className={cn(
                      "type-body-large relative flex min-h-row cursor-pointer items-center rounded-sm py-1 pr-9 pl-3 outline-none select-none",
                      "data-[highlighted]:bg-hovered-variant data-[highlighted]:outline-2 data-[highlighted]:-outline-offset-2 data-[highlighted]:outline-focus-ring",
                    )}
                  >
                    <SelectPrimitive.ItemText>{item.label}</SelectPrimitive.ItemText>
                    <SelectPrimitive.ItemIndicator className="absolute right-2">
                      <IconCheck aria-hidden="true" className="size-5" />
                    </SelectPrimitive.ItemIndicator>
                  </SelectPrimitive.Item>
                ))}
              </SelectPrimitive.Viewport>
            </SelectPrimitive.Content>
          </SelectPrimitive.Portal>
        </SelectPrimitive.Root>
      )}
    </FieldFrame>
  ),
);
Select.displayName = "Select";
