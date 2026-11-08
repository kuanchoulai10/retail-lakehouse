import { AlertDialog as AlertDialogPrimitive } from "radix-ui";
import type { ReactNode } from "react";
import { useReturnFocus } from "../../lib/useReturnFocus";
import { Button, type ButtonProps } from "../Button/Button";

export type AlertDialogProps = {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  title: string;
  description?: string;
  children?: ReactNode;
  footer?: ReactNode;
};

export function AlertDialog({
  isOpen,
  onOpenChange,
  title,
  description,
  children,
  footer,
}: AlertDialogProps) {
  const { onCloseAutoFocus } = useReturnFocus(isOpen);
  return (
    <AlertDialogPrimitive.Root open={isOpen} onOpenChange={onOpenChange}>
      <AlertDialogPrimitive.Portal>
        <AlertDialogPrimitive.Overlay className="fixed inset-0 z-50 bg-scrim" />
        <AlertDialogPrimitive.Content
          onCloseAutoFocus={onCloseAutoFocus}
          {...(description ? {} : { "aria-describedby": undefined })}
          className={[
            "fixed top-1/2 left-1/2 z-50 flex max-h-[85dvh] w-[calc(100%-2rem)] max-w-md",
            "-translate-x-1/2 -translate-y-1/2 flex-col rounded-lg bg-surface px-6 py-4 text-on-surface",
          ].join(" ")}
        >
          <AlertDialogPrimitive.Title className="type-title-large">{title}</AlertDialogPrimitive.Title>
          {description && (
            <AlertDialogPrimitive.Description className="type-body-medium mt-1 text-on-surface-variant">
              {description}
            </AlertDialogPrimitive.Description>
          )}
          {children && <div className="type-body-large mt-4 overflow-y-auto">{children}</div>}
          {footer && <div className="mt-6 flex justify-end gap-2">{footer}</div>}
        </AlertDialogPrimitive.Content>
      </AlertDialogPrimitive.Portal>
    </AlertDialogPrimitive.Root>
  );
}

export function AlertDialogCancel(props: Omit<ButtonProps, "asChild">) {
  return (
    <AlertDialogPrimitive.Cancel asChild>
      <Button styleType="outlined" {...props} />
    </AlertDialogPrimitive.Cancel>
  );
}

export function AlertDialogAction(props: Omit<ButtonProps, "asChild">) {
  return (
    <AlertDialogPrimitive.Action asChild>
      <Button {...props} />
    </AlertDialogPrimitive.Action>
  );
}

