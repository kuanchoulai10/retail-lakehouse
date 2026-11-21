import { Dialog, VisuallyHidden } from "radix-ui";
import { type ReactNode, useLayoutEffect, useRef } from "react";
import { IconX } from "../../icons";
import { cn } from "../../lib/cn";
import { useMatchesMedia } from "../../lib/useMatchesMedia";
import { useReturnFocus } from "../../lib/useReturnFocus";
import { IconButton } from "../IconButton/IconButton";

export type DrawerProps = {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  side?: "left" | "right";
  title: string;
  hideTitle?: boolean;
  /**
   * false: a side panel beside the page. No scrim, a press outside does not close it, focus is not
   * trapped, and opening moves focus to its heading. Below 768px it is modal and full width anyway.
   */
  modal?: boolean;
  /**
   * Names the record the panel shows. When it changes while open, focus moves to the heading and
   * the element focused (or pressed) just before becomes the element focus returns to on close.
   */
  contentKey?: string;
  onCloseAutoFocus?: (event: Event) => void;
  children: ReactNode;
};

export function Drawer({
  isOpen,
  onOpenChange,
  side = "right",
  title,
  hideTitle = false,
  modal = true,
  contentKey,
  onCloseAutoFocus: onCloseAutoFocusOverride,
  children,
}: DrawerProps) {
  const isWide = useMatchesMedia("(min-width: 48rem)");
  const isModal = modal || !isWide;
  const headingRef = useRef<HTMLHeadingElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const heading = (
    <Dialog.Title ref={headingRef} tabIndex={-1} className="type-title-large">
      {title}
    </Dialog.Title>
  );
  const { onCloseAutoFocus: returnFocus, remember } = useReturnFocus(isOpen);
  const shown = useRef({ isOpen, contentKey });
  useLayoutEffect(() => {
    const before = shown.current;
    shown.current = { isOpen, contentKey };
    if (before.isOpen && isOpen && before.contentKey !== contentKey) {
      remember(contentRef.current);
      headingRef.current?.focus();
    }
  }, [isOpen, contentKey, remember]);
  const onCloseAutoFocus = (event: Event) => {
    onCloseAutoFocusOverride?.(event);
    if (!event.defaultPrevented) {
      returnFocus(event);
    }
  };
  const onOpenAutoFocus = (event: Event) => {
    if (!modal) {
      event.preventDefault();
      headingRef.current?.focus();
    }
  };
  return (
    <Dialog.Root open={isOpen} onOpenChange={onOpenChange} modal={isModal}>
      <Dialog.Portal>
        {isModal ? <Dialog.Overlay className="fixed inset-0 z-50 bg-scrim" /> : null}
        <Dialog.Content
          ref={contentRef}
          onOpenAutoFocus={onOpenAutoFocus}
          onCloseAutoFocus={onCloseAutoFocus}
          onInteractOutside={isModal ? undefined : (event) => event.preventDefault()}
          aria-describedby={undefined}
          className={cn(
            "fixed inset-y-0 z-50 flex w-full flex-col bg-surface text-on-surface",
            modal ? "max-w-sm" : "md:max-w-sm",
            !modal && (side === "right" ? "border-l border-outline" : "border-r border-outline"),
            side === "right" ? "right-0" : "left-0",
          )}
        >
          <div className="flex items-center justify-between gap-2 px-6 pt-4">
            {hideTitle ? <VisuallyHidden.Root>{heading}</VisuallyHidden.Root> : heading}
            <Dialog.Close asChild>
              <IconButton aria-label="Close" styleType="ghost" icon={<IconX />} />
            </Dialog.Close>
          </div>
          <div className="type-body-large flex-1 overflow-y-auto px-6 py-4">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
