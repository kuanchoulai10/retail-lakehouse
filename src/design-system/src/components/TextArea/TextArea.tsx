import { forwardRef, type ComponentProps } from "react";
import { cn } from "../../lib/cn";
import { FieldFrame, fieldControlStyle, type FieldProps } from "../../lib/Field";

export type TextAreaProps = Omit<ComponentProps<"textarea">, "required"> & FieldProps;

export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(
  ({ label, description, invalid, invalidMessage, required, id, className, ...rest }, ref) => (
    <FieldFrame {...{ label, description, invalid, invalidMessage, required, id }}>
      {(controlProps) => (
        <textarea
          ref={ref}
          className={cn(fieldControlStyle, "min-h-control py-2", className)}
          {...rest}
          {...controlProps}
        />
      )}
    </FieldFrame>
  ),
);
TextArea.displayName = "TextArea";
