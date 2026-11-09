import { http, HttpResponse } from "msw";
import { server } from "../test/mswServer";
import { ApiError } from "./apiError";
import { getTable, listTables, pauseTable } from "./generated/tables/tables";
import { getGetNamespaceUrl } from "./generated/namespaces/namespaces";

describe("apiFetch, through the generated client", () => {
  it("prefixes the path with /console/api, asks for JSON and returns the body", async () => {
    let seen: Request | undefined;
    server.use(
      http.get("/console/api/v1/tables", ({ request }) => {
        seen = request;
        return HttpResponse.json([{ uuid: "a" }]);
      }),
    );

    const body = await listTables();

    expect(body).toEqual([{ uuid: "a" }]);
    expect(seen?.headers.get("Accept")).toBe("application/json");
  });

  it("throws an ApiError with the status and FastAPI's detail on a non-2xx", async () => {
    server.use(
      http.get("/console/api/v1/tables/:uuid", () =>
        HttpResponse.json({ detail: "table not found" }, { status: 404 }),
      ),
    );

    const error = await getTable("missing").catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 404, detail: "table not found" });
  });

  it("falls back to the status text when the error body is not JSON", async () => {
    server.use(
      http.get("/console/api/v1/tables", () =>
        new HttpResponse("boom", { status: 502, statusText: "Bad Gateway" }),
      ),
    );

    const error = await listTables().catch((e: unknown) => e);

    expect(error).toMatchObject({ status: 502, detail: "Bad Gateway" });
  });

  it("sends a JSON body with its content type, and none when there is no body", async () => {
    const seen: { contentType: string | null; body: string }[] = [];
    server.use(
      http.post("/console/api/v1/tables/:uuid/pause", async ({ request }) => {
        seen.push({ contentType: request.headers.get("Content-Type"), body: await request.text() });
        return HttpResponse.json({ uuid: "u" });
      }),
    );

    await pauseTable("u");

    expect(seen).toEqual([{ contentType: null, body: "" }]);
  });

  it("encodes path parameters, so a namespace joined by U+001F and a slash round-trip", () => {
    expect(getGetNamespaceUrl("sales", "a\u001fb/c")).toBe("/v1/catalogs/sales/namespaces/a%1Fb%2Fc");
  });
});
