import { useId, type ReactNode } from "react";
import { cn } from "./cn";

export type FieldProps = {
  label: ReactNode;
  description?: string;
  invalid?: boolean;
  invalidMessage?: string;
  required?: boolean;
  hideLabel?: boolean;
};

export type FieldControlProps = {
  id: string;
  "aria-invalid": true | undefined;
  "aria-describedby": string | undefined;
  required: true | undefined;
};

type FieldFrameProps = FieldProps & {
  id?: string;
  className?: string;
  children: (controlProps: FieldControlProps) => ReactNode;
};

export const fieldControlStyle = [
  "w-full rounded-md border border-outline bg-surface px-3 text-on-surface type-body-large",
  "placeholder:text-on-surface-variant",
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus-ring",
  "aria-invalid:border-2 aria-invalid:border-negative",
  "disabled:cursor-not-allowed disabled:border-transparent disabled:bg-disabled disabled:text-on-disabled",
];

export function FieldFrame({
  id,
  label,
  description,
  invalid = false,
  invalidMessage,
  required = false,
  hideLabel = false,
  className,
  children,
}: FieldFrameProps) {
  const generatedId = useId();
  const controlId = id ?? generatedId;
  const descriptionId = description ? `${controlId}-description` : undefined;
  const messageId = invalid && invalidMessage ? `${controlId}-message` : undefined;
  const describedBy = [descriptionId, messageId].filter(Boolean).join(" ") || undefined;

  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <label htmlFor={controlId} className={cn("type-label-large text-on-surface", hideLabel && "sr-only")}>
        {label}
        {required && (
          <span aria-hidden="true" className="text-negative-text">
            {" *"}
          </span>
        )}
      </label>
      {description && (
        <p id={descriptionId} className="type-body-small text-on-surface-variant">
          {description}
        </p>
      )}
      {children({
        id: controlId,
        "aria-invalid": invalid || undefined,
        "aria-describedby": describedBy,
        required: required || undefined,
      })}
      <div aria-live="polite" className="empty:-mt-1">
        {messageId && (
          <p id={messageId} className="type-body-small text-negative-text">
            {invalidMessage}
          </p>
        )}
      </div>
    </div>
  );
}
