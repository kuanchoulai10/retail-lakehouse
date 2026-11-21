import { ApiError } from "@/api/apiError";

// A record read by id is gone when the API answers 404 (it no longer exists) or 422 (the id cannot
// name one, which is what a link from before the prefixed ids carries). Either way the link points at nothing.
export function isGone(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 404 || error.status === 422);
}
