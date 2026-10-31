import { describe, expect, it, vi } from "vitest";
import { ApiError, apiGet, apiSend } from "./client";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("apiGet", () => {
  it("prefixes the path with /console/api and returns the JSON body", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, [{ uuid: "a" }]));
    vi.stubGlobal("fetch", fetchMock);

    const body = await apiGet<{ uuid: string }[]>("/v1/tables");

    expect(body).toEqual([{ uuid: "a" }]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/console/api/v1/tables");
  });

  it("throws an ApiError with the status and the JSON detail on a non-2xx", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(404, { detail: "table not found" })),
    );

    const error = await apiGet("/v1/tables/missing").catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 404, detail: "table not found" });
  });

  it("falls back to the status text when the error body is not JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(new Response("boom", { status: 502, statusText: "Bad Gateway" })),
    );

    const error = await apiGet("/v1/tables").catch((e: unknown) => e);

    expect(error).toMatchObject({ status: 502, detail: "Bad Gateway" });
  });
});

describe("apiSend", () => {
  it("sends the method and a JSON body to the prefixed path", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(202, { accepted: true }));
    vi.stubGlobal("fetch", fetchMock);

    const body = await apiSend<{ accepted: boolean }>("POST", "/v1/tables/u/maintenance", {
      operations: ["expire_snapshots"],
    });

    expect(body).toEqual({ accepted: true });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/console/api/v1/tables/u/maintenance");
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ operations: ["expire_snapshots"] }));
    expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
  });

  it("sends no body when none is given", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { uuid: "u" }));
    vi.stubGlobal("fetch", fetchMock);

    await apiSend("POST", "/v1/tables/u/pause");

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.body).toBeUndefined();
  });
});
