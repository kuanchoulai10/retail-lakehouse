import { ApiError, errorDetail } from "./apiError";

// Every request goes through the console's nginx, which strips this prefix.
export const API_PREFIX = "/console/api";

// The generated client's fetch: prefixes the path, sends JSON, and turns a non-2xx reply
// into an ApiError carrying FastAPI's `detail`, so pages show the backend's message.
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body !== undefined && init.body !== null && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_PREFIX}${path}`, { ...init, headers });
  if (!response.ok) {
    throw new ApiError(response.status, await errorDetail(response));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export type { ErrorType } from "./apiError";

export default apiFetch;
