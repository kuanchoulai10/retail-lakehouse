import { delay, http } from "msw";

// A handler that never answers one API path, so the page stays in its loading state.
export function apiPending(path: string, method: "get" | "post" = "get") {
  return http[method](`*${path}`, async () => {
    await delay("infinite");
    return new Response(null);
  });
}
