import { ApiError } from "@/api/client";
import { errorMessage } from "@/format";

// The message for a failed update. A 409 means someone changed the object after this page
// loaded it, so the user is told to reload rather than shown the raw version mismatch.
export function updateErrorMessage(error: unknown, objectKind: string): string {
  if (isConflict(error)) {
    return `This ${objectKind} changed since you loaded it, reload and try again.`;
  }
  return errorMessage(error);
}

export function isConflict(error: unknown): boolean {
  return error instanceof ApiError && error.status === 409;
}
