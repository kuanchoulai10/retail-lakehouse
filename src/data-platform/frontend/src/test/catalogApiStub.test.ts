import { callsTo, stubCatalogApi } from "./catalogApiStub";
import { jsonResponse } from "./fixtures";

describe("stubCatalogApi", () => {
  it("answers through the network layer instead of replacing fetch", async () => {
    stubCatalogApi({ "GET /v1/catalogs": () => jsonResponse([{ name: "iceberg" }]) });

    expect(vi.isMockFunction(globalThis.fetch)).toBe(false);
    const response = await fetch("/console/api/v1/catalogs");
    expect(await response.json()).toEqual([{ name: "iceberg" }]);
  });

  it("matches the query string and prefix keys, and records each call with its JSON body", async () => {
    const calls = stubCatalogApi({
      "GET /v1/catalogs?page=2": () => jsonResponse([]),
      "POST /v1/catalogs/*": (body) => jsonResponse(body, 201),
    });

    await fetch("/console/api/v1/catalogs?page=2");
    const created = await fetch("/console/api/v1/catalogs/iceberg/namespaces", {
      method: "POST",
      body: JSON.stringify({ namespace: ["sales"] }),
    });

    expect(created.status).toBe(201);
    expect(await created.json()).toEqual({ namespace: ["sales"] });
    expect(callsTo(calls, "GET", "/v1/catalogs?page=2")).toHaveLength(1);
    expect(callsTo(calls, "POST", "/v1/catalogs/iceberg/namespaces")[0]?.body).toEqual({
      namespace: ["sales"],
    });
  });

  it("answers 500 for a request no route stubs, so a test sees it instead of hanging", async () => {
    stubCatalogApi({});

    const response = await fetch("/console/api/v1/unknown");

    expect(response.status).toBe(500);
    expect(await response.json()).toEqual({ detail: "no stub for GET /v1/unknown" });
  });
});
