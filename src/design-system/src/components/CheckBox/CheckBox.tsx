import { Checkbox as CheckboxPrimitive } from "radix-ui";
import { forwardRef, useId, type ComponentProps } from "react";
import { cn } from "../../lib/cn";
import { SerendieSymbolCheck } from "../../icons";

export type CheckBoxProps = Omit<ComponentProps<typeof CheckboxPrimitive.Root>, "children"> & {
  label: string;
};

export const CheckBox = forwardRef<HTMLButtonElement, CheckBoxProps>(
  ({ label, id, className, ...rest }, ref) => {
    const generatedId = useId();
    const controlId = id ?? generatedId;
    return (
      <div className="flex min-h-control items-center gap-2">
        <CheckboxPrimitive.Root
          ref={ref}
          id={controlId}
          className={cn(
            "flex size-6 shrink-0 cursor-pointer items-center justify-center rounded-sm border-2 border-outline-dim bg-surface",
            "data-[state=checked]:border-primary-container data-[state=checked]:bg-primary-container",
            "data-[state=checked]:text-on-primary-container",
            "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus-ring",
            "disabled:cursor-not-allowed disabled:border-transparent disabled:bg-disabled disabled:text-on-disabled",
            className,
          )}
          {...rest}
        >
          <CheckboxPrimitive.Indicator>
            <SerendieSymbolCheck aria-hidden="true" className="size-4" />
          </CheckboxPrimitive.Indicator>
        </CheckboxPrimitive.Root>
        <label
          htmlFor={controlId}
          className={cn(
            "type-body-large flex min-h-control flex-1 cursor-pointer items-center text-on-surface",
            rest.disabled && "cursor-not-allowed text-on-disabled",
          )}
        >
          {label}
        </label>
      </div>
    );
  },
);
CheckBox.displayName = "CheckBox";
