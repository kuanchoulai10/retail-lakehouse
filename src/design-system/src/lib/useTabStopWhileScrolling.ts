import { useEffect, useLayoutEffect } from "react";

function update(element: HTMLElement) {
  if (element.scrollHeight > element.clientHeight) {
    element.setAttribute("tabindex", "0");
  } else {
    element.removeAttribute("tabindex");
  }
}

// Gives `element`, a scroll container, a tab stop while `content` is taller than it, so the keyboard
// can scroll content that has no control of its own. Checked after every render, before paint, so
// new content counts at once, and whenever either changes size, as a resized window does. The
// attribute is set on the element directly: the caller does not pass tabIndex.
export function useTabStopWhileScrolling(element: HTMLElement | null, content: HTMLElement | null): void {
  useLayoutEffect(() => {
    if (element !== null) {
      update(element);
    }
  });
  useEffect(() => {
    if (element === null || typeof ResizeObserver === "undefined") {
      return;
    }
    const observer = new ResizeObserver(() => update(element));
    observer.observe(element);
    if (content !== null) {
      observer.observe(content);
    }
    return () => observer.disconnect();
  }, [element, content]);
}
