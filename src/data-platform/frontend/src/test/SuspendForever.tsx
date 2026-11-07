import { use } from "react";

const never = new Promise<never>(() => {});

// A page that never finishes rendering. A navigation to it stays pending, so the page that
// navigated keeps rendering and re-rendering, as it does while a real transition is in flight.
export function SuspendForever() {
  return use(never);
}

// Lets the mutation settle and any refetch it would cause go out.
export function settle(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 50));
}
