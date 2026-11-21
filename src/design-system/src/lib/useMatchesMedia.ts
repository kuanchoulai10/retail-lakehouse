import { useSyncExternalStore } from "react";

export function useMatchesMedia(query: string): boolean {
  const subscribe = (onChange: () => void) => {
    if (typeof window.matchMedia !== "function") {
      return () => {};
    }
    const list = window.matchMedia(query);
    list.addEventListener("change", onChange);
    return () => list.removeEventListener("change", onChange);
  };
  const getSnapshot = () =>
    typeof window.matchMedia === "function" ? window.matchMedia(query).matches : true;
  return useSyncExternalStore(subscribe, getSnapshot, () => true);
}
