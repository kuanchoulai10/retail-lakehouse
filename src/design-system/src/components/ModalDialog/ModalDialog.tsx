import { Dialog } from "radix-ui";
import type { ReactNode } from "react";
import { SerendieSymbolClose } from "../../icons";
import { useReturnFocus } from "../../lib/useReturnFocus";
import { IconButton } from "../IconButton/IconButton";

export type ModalDialogProps = {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  title: string;
  description?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
};

export function ModalDialog({
  isOpen,
  onOpenChange,
  title,
  description,
  children,
  footer,
}: ModalDialogProps) {
  const { onCloseAutoFocus } = useReturnFocus(isOpen);
  return (
    <Dialog.Root open={isOpen} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-scrim" />
        <Dialog.Content
          onCloseAutoFocus={onCloseAutoFocus}
          {...(description ? {} : { "aria-describedby": undefined })}
          className={[
            "fixed inset-0 z-50 flex flex-col bg-surface text-on-surface",
            "md:inset-auto md:top-1/2 md:left-1/2 md:max-h-[85dvh] md:w-[calc(100%-2rem)] md:max-w-lg",
            "md:-translate-x-1/2 md:-translate-y-1/2 md:rounded-lg",
          ].join(" ")}
        >
          <div className="flex items-start justify-between gap-2 px-6 pt-4">
            <div className="flex min-h-touch flex-col justify-center gap-1">
              <Dialog.Title className="type-title-large">{title}</Dialog.Title>
              {description && (
                <Dialog.Description className="type-body-medium text-on-surface-variant">
                  {description}
                </Dialog.Description>
              )}
            </div>
            <Dialog.Close asChild>
              <IconButton aria-label="Close" styleType="ghost" icon={<SerendieSymbolClose />} />
            </Dialog.Close>
          </div>
          <div className="type-body-large flex-1 overflow-y-auto px-6 py-4">{children}</div>
          {footer && <div className="flex justify-end gap-2 px-6 pt-2 pb-4">{footer}</div>}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
