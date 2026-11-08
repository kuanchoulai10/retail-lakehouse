import { useCallback, useLayoutEffect, useRef } from "react";

const FOCUSABLE = "button, a[href], input, select, textarea, summary, [role='button'], [tabindex]";
const MENU = "[role='menu'], [role='menubar']";

function isFocusTarget(element: Element | null): element is HTMLElement {
  return element instanceof HTMLElement && element !== element.ownerDocument.body;
}

function isOutsideMenu(element: HTMLElement | null): element is HTMLElement {
  return element !== null && element.isConnected && element.closest(MENU) === null;
}

// One document-wide record shared by every overlay: the last element focused outside a menu (so a
// dialog opened from a menu item returns to the menu's trigger once the menu has unmounted) and
// the element the last pointer press landed on (for triggers that drop focus when clicked). A key
// press clears the pointer record so a stale press is never used.
const focusHistory = { lastFocusedOutsideMenu: null as HTMLElement | null, lastPointerTarget: null as HTMLElement | null };

function installFocusHistory(doc: Document) {
  doc.addEventListener(
    "focusin",
    (event) => {
      const target = event.target;
      if (target instanceof HTMLElement && isOutsideMenu(target)) {
        focusHistory.lastFocusedOutsideMenu = target;
      }
    },
    true,
  );
  doc.addEventListener(
    "pointerdown",
    (event) => {
      const target = event.target instanceof Element ? event.target.closest(FOCUSABLE) : null;
      focusHistory.lastPointerTarget = target instanceof HTMLElement ? target : null;
    },
    true,
  );
  doc.addEventListener(
    "keydown",
    () => {
      focusHistory.lastPointerTarget = null;
    },
    true,
  );
}

if (typeof document !== "undefined") {
  installFocusHistory(document);
}

function focusBeforeOpening(): HTMLElement | null {
  const active = document.activeElement;
  if (isFocusTarget(active) && isOutsideMenu(active)) {
    return active;
  }
  if (isOutsideMenu(focusHistory.lastPointerTarget)) {
    return focusHistory.lastPointerTarget;
  }
  return isOutsideMenu(focusHistory.lastFocusedOutsideMenu) ? focusHistory.lastFocusedOutsideMenu : null;
}

export function useReturnFocus(isOpen: boolean) {
  const returnTo = useRef<HTMLElement | null>(null);

  useLayoutEffect(() => {
    if (!isOpen) {
      return;
    }
    returnTo.current = focusBeforeOpening();
  }, [isOpen]);

  const onCloseAutoFocus = useCallback((event: Event) => {
    const target = returnTo.current;
    if (target?.isConnected) {
      event.preventDefault();
      target.focus();
    }
  }, []);

  return { onCloseAutoFocus };
}
