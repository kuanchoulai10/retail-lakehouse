import { http, HttpResponse } from "msw";

// A handler that fails one API path the way FastAPI does, with its detail.
export function apiError(method: "get" | "post" | "put" | "delete", path: string, detail: string, status = 502) {
  return http[method](`*${path}`, () => HttpResponse.json({ detail }, { status }));
}
