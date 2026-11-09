import { describe, expect, it } from "vitest";
import { ApiError } from "./apiError";
import { retryQuery } from "./retryQuery";

describe("retryQuery", () => {
  it("does not retry a client error", () => {
    expect(retryQuery(0, new ApiError(404, "table x is not in the catalog"))).toBe(false);
    expect(retryQuery(0, new ApiError(422, "bad input"))).toBe(false);
  });

  it("retries a server error up to three times", () => {
    expect(retryQuery(0, new ApiError(500, "boom"))).toBe(true);
    expect(retryQuery(2, new ApiError(503, "unavailable"))).toBe(true);
    expect(retryQuery(3, new ApiError(500, "boom"))).toBe(false);
  });

  it("retries a network error up to three times", () => {
    expect(retryQuery(0, new TypeError("Failed to fetch"))).toBe(true);
    expect(retryQuery(3, new TypeError("Failed to fetch"))).toBe(false);
  });
});
