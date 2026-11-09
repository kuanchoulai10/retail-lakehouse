import { delay, http } from "msw";

// A handler that never answers one API path, so the page stays in its loading state.
export function apiPending(path: string) {
  return http.get(`*${path}`, async () => {
    await delay("infinite");
    return new Response(null);
  });
}
