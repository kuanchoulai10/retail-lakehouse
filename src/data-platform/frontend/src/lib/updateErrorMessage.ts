import { ApiError } from "@/api/client";
import { errorMessage } from "@/format";

// The message for a failed update. A 409 means someone changed the object after this page
// loaded it, so the user is told to reload rather than shown the raw version mismatch,
// unless the API says part of the change was applied: that message is shown as it is.
export function updateErrorMessage(error: unknown, objectKind: string): string {
  if (isConflict(error) && !reportsAppliedChange(error)) {
    return `This ${objectKind} changed since you loaded it, reload and try again.`;
  }
  return errorMessage(error);
}

export function isConflict(error: unknown): boolean {
  return error instanceof ApiError && error.status === 409;
}

// The backend starts such a message with what landed, e.g. "removals were applied; reload ...".
function reportsAppliedChange(error: unknown): boolean {
  return error instanceof ApiError && /\bwere applied\b/.test(error.detail);
}
