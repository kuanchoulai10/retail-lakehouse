import type { StatusBadgeProps } from "@retail-lakehouse/design-system";

export type StatusTone = StatusBadgeProps["status"];

// Colour only for status: a succeeded run is positive, a failure negative, a due operation, a
// truncated count or a run waiting to retry a notice; every other state (managed, unmanaged,
// running, cancelled, …) stays neutral.
export function statusTone(status: string): StatusTone {
  switch (status.toLowerCase()) {
    case "succeeded":
      return "positive";
    case "failed":
    case "error":
      return "negative";
    case "due":
    case "truncated":
    case "retry_waiting":
      return "notice";
    default:
      return "neutral";
  }
}
