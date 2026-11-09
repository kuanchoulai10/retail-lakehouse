import { ApiError } from "./apiError";

const MAX_RETRIES = 3;

export function retryQuery(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status < 500) return false;
  return failureCount < MAX_RETRIES;
}
