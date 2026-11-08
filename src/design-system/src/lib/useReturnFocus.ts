import { useCallback, useLayoutEffect, useRef } from "react";

export function useReturnFocus(isOpen: boolean) {
  const returnTo = useRef<HTMLElement | null>(null);

  useLayoutEffect(() => {
    if (isOpen && document.activeElement instanceof HTMLElement) {
      returnTo.current = document.activeElement;
    }
  }, [isOpen]);

  const onCloseAutoFocus = useCallback((event: Event) => {
    event.preventDefault();
    returnTo.current?.focus();
  }, []);

  return { onCloseAutoFocus };
}
