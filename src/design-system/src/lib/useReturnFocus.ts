import { useCallback, useEffect, useLayoutEffect, useRef } from "react";

const FOCUSABLE = "button, a[href], input, select, textarea, summary, [role='button'], [tabindex]";

function isFocusTarget(element: Element | null): element is HTMLElement {
  return element instanceof HTMLElement && element !== element.ownerDocument.body;
}

export function useReturnFocus(isOpen: boolean) {
  const returnTo = useRef<HTMLElement | null>(null);
  const lastPointerTarget = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const remember = (event: PointerEvent) => {
      const target = event.target instanceof Element ? event.target.closest(FOCUSABLE) : null;
      lastPointerTarget.current = target instanceof HTMLElement ? target : null;
    };
    document.addEventListener("pointerdown", remember, true);
    return () => document.removeEventListener("pointerdown", remember, true);
  }, []);

  useLayoutEffect(() => {
    if (!isOpen) {
      return;
    }
    const active = document.activeElement;
    returnTo.current = isFocusTarget(active) ? active : lastPointerTarget.current;
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
