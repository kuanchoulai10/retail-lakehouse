import { forwardRef, type ComponentProps } from "react";
import { cn } from "../../lib/cn";
import { FieldFrame, fieldControlStyle, type FieldProps } from "../../lib/Field";

export type TextFieldProps = Omit<ComponentProps<"input">, "required"> & FieldProps;

export const TextField = forwardRef<HTMLInputElement, TextFieldProps>(
  ({ label, description, invalid, invalidMessage, required, hideLabel, id, className, ...rest }, ref) => (
    <FieldFrame {...{ label, description, invalid, invalidMessage, required, hideLabel, id }}>
      {(controlProps) => (
        <input
          ref={ref}
          className={cn(fieldControlStyle, "h-control", className)}
          {...rest}
          {...controlProps}
        />
      )}
    </FieldFrame>
  ),
);
TextField.displayName = "TextField";
