import type { StatusBadgeProps } from "@retail-lakehouse/design-system";

export type StatusTone = StatusBadgeProps["status"];

// Colour only for status: a succeeded run is positive, a failure negative, a due operation or a
// truncated count a notice; every other state (active, paused, running, …) stays neutral.
export function statusTone(status: string): StatusTone {
  switch (status.toLowerCase()) {
    case "succeeded":
      return "positive";
    case "failed":
    case "error":
      return "negative";
    case "due":
    case "truncated":
      return "notice";
    default:
      return "neutral";
  }
}
