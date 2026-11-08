import { Dialog, VisuallyHidden } from "radix-ui";
import type { ReactNode } from "react";
import { SerendieSymbolClose } from "../../icons";
import { cn } from "../../lib/cn";
import { useReturnFocus } from "../../lib/useReturnFocus";
import { IconButton } from "../IconButton/IconButton";

export type DrawerProps = {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  side?: "left" | "right";
  title: string;
  hideTitle?: boolean;
  onCloseAutoFocus?: (event: Event) => void;
  children: ReactNode;
};

export function Drawer({
  isOpen,
  onOpenChange,
  side = "right",
  title,
  hideTitle = false,
  onCloseAutoFocus: onCloseAutoFocusOverride,
  children,
}: DrawerProps) {
  const heading = <Dialog.Title className="type-title-large">{title}</Dialog.Title>;
  const { onCloseAutoFocus: returnFocus } = useReturnFocus(isOpen);
  const onCloseAutoFocus = (event: Event) => {
    onCloseAutoFocusOverride?.(event);
    if (!event.defaultPrevented) {
      returnFocus(event);
    }
  };
  return (
    <Dialog.Root open={isOpen} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-scrim" />
        <Dialog.Content
          onCloseAutoFocus={onCloseAutoFocus}
          aria-describedby={undefined}
          className={cn(
            "fixed inset-y-0 z-50 flex w-full max-w-sm flex-col bg-surface text-on-surface",
            side === "right" ? "right-0" : "left-0",
          )}
        >
          <div className="flex items-center justify-between gap-2 px-6 pt-4">
            {hideTitle ? <VisuallyHidden.Root>{heading}</VisuallyHidden.Root> : heading}
            <Dialog.Close asChild>
              <IconButton aria-label="Close" styleType="ghost" icon={<SerendieSymbolClose />} />
            </Dialog.Close>
          </div>
          <div className="type-body-large flex-1 overflow-y-auto px-6 py-4">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
