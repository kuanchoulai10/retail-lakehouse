import { Switch as SwitchPrimitive } from "radix-ui";
import { forwardRef, useId, type ComponentProps } from "react";
import { cn } from "../../lib/cn";

export type SwitchProps = Omit<ComponentProps<typeof SwitchPrimitive.Root>, "children"> & {
  label: string;
};

export const Switch = forwardRef<HTMLButtonElement, SwitchProps>(
  ({ label, id, className, ...rest }, ref) => {
    const generatedId = useId();
    const controlId = id ?? generatedId;
    return (
      <div className="flex min-h-control items-center gap-2">
        <SwitchPrimitive.Root
          ref={ref}
          id={controlId}
          className={cn(
            "h-8 w-14 shrink-0 cursor-pointer rounded-full bg-outline",
            "data-[state=checked]:bg-primary-container",
            "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus-ring",
            "disabled:cursor-not-allowed disabled:bg-disabled",
            className,
          )}
          {...rest}
        >
          <SwitchPrimitive.Thumb
            className={cn(
              "block size-6 translate-x-1 rounded-full bg-surface transition-transform motion-reduce:transition-none",
              "data-[state=checked]:translate-x-7 data-[state=checked]:bg-on-primary-container",
            )}
          />
        </SwitchPrimitive.Root>
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
Switch.displayName = "Switch";
