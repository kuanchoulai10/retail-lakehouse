import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi } from "vitest";
import type { NamespaceSummaryApiResponse } from "../api/catalogTypes";
import { bodyOf, callsTo, catalogFixture, stubCatalogApi, type StubHandler } from "../test/catalogApiStub";
import { jsonResponse } from "../test/fixtures";
import { settle, SuspendForever } from "../test/SuspendForever";
import { CatalogPage } from "./CatalogPage";
import { NamespacePage } from "./NamespacePage";

function renderAt(path: string, catalogsPage: ReactNode = <p>catalogs list</p>) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/catalogs" element={catalogsPage} />
          <Route path="/catalogs/:catalog" element={<CatalogPage />} />
          <Route path="/catalogs/:catalog/namespaces/:namespace" element={<NamespacePage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return client;
}

const NAMESPACES: NamespaceSummaryApiResponse[] = [
  { catalog: "iceberg", namespace: ["retail"] },
  { catalog: "iceberg", namespace: ["a.b"] },
];

function stubCatalog(extra: Record<string, StubHandler> = {}) {
  return stubCatalogApi({
    "GET /v1/catalogs/iceberg": () => jsonResponse(catalogFixture()),
    "GET /v1/catalogs/iceberg/namespaces": () => jsonResponse(NAMESPACES),
    ...extra,
  });
}

async function openAction(user: ReturnType<typeof userEvent.setup>, label: string) {
  await user.click(screen.getByRole("button", { name: "Actions" }));
  await user.click(await screen.findByRole("menuitem", { name: label }));
}

// These tests type whole forms, which takes seconds under a loaded parallel run.
describe("CatalogPage", { timeout: 15_000 }, () => {
  it("catalog page lists namespaces with breadcrumbs", async () => {
    stubCatalog();
    renderAt("/catalogs/iceberg");
    expect(await screen.findByRole("link", { name: "retail" })).toHaveAttribute(
      "href",
      "/catalogs/iceberg/namespaces/retail",
    );
    const crumbs = screen.getByRole("navigation", { name: "Breadcrumb" });
    expect(within(crumbs).getByRole("link", { name: "Catalogs" })).toHaveAttribute("href", "/catalogs");
    expect(within(crumbs).getByText("iceberg")).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("heading", { level: 1, name: "iceberg" })).toBeInTheDocument();
    const storage = screen.getByRole("region", { name: "Storage" });
    expect(within(storage).getByText("S3")).toBeInTheDocument();
    expect(within(storage).getByText("http://rustfs:9000")).toBeInTheDocument();
    const properties = screen.getByRole("region", { name: "Properties" });
    expect(within(properties).getByText("owner")).toBeInTheDocument();
  });

  it("namespace path with a dot part links and loads", async () => {
    const user = userEvent.setup();
    const calls = stubCatalog({
      "GET /v1/catalogs/iceberg/namespaces/a.b": () =>
        jsonResponse({ catalog: "iceberg", namespace: ["a.b"], properties: {} }),
      "GET /v1/catalogs/iceberg/namespaces?parent=a.b": () => jsonResponse([]),
      "GET /v1/catalogs/iceberg/namespaces/a.b/tables": () => jsonResponse([]),
      "GET /v1/catalogs/iceberg/namespaces/a.b/views": () => jsonResponse([]),
      "GET /v1/catalogs/iceberg/namespaces/a.b/generic-tables": () => jsonResponse([]),
    });
    renderAt("/catalogs/iceberg");
    await user.click(await screen.findByRole("link", { name: "a.b" }));
    expect(await screen.findByRole("heading", { level: 1, name: "a.b" })).toBeInTheDocument();
    expect(callsTo(calls, "GET", "/v1/catalogs/iceberg/namespaces/a.b")).toHaveLength(1);
  });

  it("creates a top-level namespace and refetches the list", async () => {
    const user = userEvent.setup();
    let namespaces = NAMESPACES;
    const calls = stubCatalog({
      "GET /v1/catalogs/iceberg/namespaces": () => jsonResponse(namespaces),
      "POST /v1/catalogs/iceberg/namespaces": () => {
        namespaces = [...namespaces, { catalog: "iceberg", namespace: ["x.y"] }];
        return jsonResponse({ catalog: "iceberg", namespace: ["x.y"], properties: {} }, 201);
      },
    });
    renderAt("/catalogs/iceberg");
    await screen.findByRole("link", { name: "retail" });
    await user.click(screen.getByRole("button", { name: "New namespace" }));
    const dialog = screen.getByRole("dialog");
    await user.type(within(dialog).getByLabelText("Name"), "x.y");
    await user.type(within(dialog).getByLabelText(/Location/), "s3://warehouse/xy");
    await user.click(within(dialog).getByRole("button", { name: "Create" }));
    expect(await screen.findByRole("link", { name: "x.y" })).toBeInTheDocument();
    expect(bodyOf(calls, "POST", "/v1/catalogs/iceberg/namespaces")).toEqual({
      namespace: ["x.y"],
      properties: { location: "s3://warehouse/xy" },
    });
  });

  it("catalog edit conflict shows reload message", async () => {
    const user = userEvent.setup();
    const calls = stubCatalog({
      "PUT /v1/catalogs/iceberg": () =>
        jsonResponse({ detail: "entity version 7 does not match 8" }, 409),
    });
    renderAt("/catalogs/iceberg");
    await screen.findByRole("link", { name: "retail" });
    await openAction(user, "Edit");
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByLabelText("Default base location")).toHaveValue("s3://warehouse/iceberg");
    expect(within(dialog).getByLabelText("Endpoint")).toHaveValue("http://rustfs:9000");
    await user.clear(within(dialog).getByLabelText("Region"));
    await user.type(within(dialog).getByLabelText("Region"), "eu-west-1");
    await user.click(within(dialog).getByRole("button", { name: "Save" }));

    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "This catalog changed since you loaded it, reload and try again.",
    );
    expect(bodyOf(calls, "PUT", "/v1/catalogs/iceberg")).toEqual({
      entity_version: 7,
      default_base_location: "s3://warehouse/iceberg",
      properties: { owner: "data" },
      storage_config: {
        storage_type: "S3",
        allowed_locations: ["s3://warehouse/iceberg/"],
        region: "eu-west-1",
        endpoint: "http://rustfs:9000",
        sts_unavailable: true,
        path_style_access: true,
      },
    });

    await user.click(within(dialog).getByRole("button", { name: "Reload" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await vi.waitFor(() =>
      expect(callsTo(calls, "GET", "/v1/catalogs/iceberg").length).toBeGreaterThan(1),
    );
  });

  it("saves an edit and refetches the catalog", async () => {
    const user = userEvent.setup();
    const calls = stubCatalog({
      "PUT /v1/catalogs/iceberg": () => jsonResponse(catalogFixture({ entity_version: 8 })),
    });
    renderAt("/catalogs/iceberg");
    await screen.findByRole("link", { name: "retail" });
    await openAction(user, "Edit");
    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Save" }));
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(callsTo(calls, "GET", "/v1/catalogs/iceberg").length).toBeGreaterThan(1);
  });

  it("shows polaris's message when a namespace in the list cannot be deleted", async () => {
    const user = userEvent.setup();
    stubCatalog({
      "DELETE /v1/catalogs/iceberg/namespaces/retail": () =>
        jsonResponse({ detail: "Namespace retail is not empty" }, 409),
    });
    renderAt("/catalogs/iceberg");
    await screen.findByRole("link", { name: "retail" });
    await user.click(screen.getByRole("button", { name: "Delete retail" }));
    await user.type(screen.getByLabelText(/to confirm/i), "retail");
    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Namespace retail is not empty");
  });

  it("deleting the catalog goes back to the catalogs list", async () => {
    const user = userEvent.setup();
    const calls = stubCatalog({ "DELETE /v1/catalogs/iceberg": () => new Response(null, { status: 204 }) });
    renderAt("/catalogs/iceberg");
    await screen.findByRole("link", { name: "retail" });
    await openAction(user, "Delete");
    await user.type(screen.getByLabelText(/to confirm/i), "iceberg");
    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(await screen.findByText("catalogs list")).toBeInTheDocument();
    expect(callsTo(calls, "DELETE", "/v1/catalogs/iceberg")).toHaveLength(1);
  });

  it("never refetches the deleted catalog while the navigation is still pending", async () => {
    const user = userEvent.setup();
    const calls = stubCatalog({ "DELETE /v1/catalogs/iceberg": () => new Response(null, { status: 204 }) });
    renderAt("/catalogs/iceberg", <SuspendForever />);
    await screen.findByRole("link", { name: "retail" });
    await openAction(user, "Delete");
    await user.type(screen.getByLabelText(/to confirm/i), "iceberg");
    await user.click(screen.getByRole("button", { name: "Delete" }));
    await vi.waitFor(() => expect(callsTo(calls, "DELETE", "/v1/catalogs/iceberg")).toHaveLength(1));
    await settle();
    expect(callsTo(calls, "GET", "/v1/catalogs/iceberg")).toHaveLength(1);
    expect(callsTo(calls, "GET", "/v1/catalogs/iceberg/namespaces")).toHaveLength(1);
  });

  it("saves with the version that was loaded when the dialog opened", async () => {
    const user = userEvent.setup();
    let version = 7;
    const calls = stubCatalog({
      "GET /v1/catalogs/iceberg": () => jsonResponse(catalogFixture({ entity_version: version })),
      "PUT /v1/catalogs/iceberg": () => jsonResponse({ detail: "changed" }, 409),
    });
    const client = renderAt("/catalogs/iceberg");
    await screen.findByRole("link", { name: "retail" });
    await openAction(user, "Edit");
    version = 8;
    await client.invalidateQueries({ queryKey: ["catalog", "iceberg"] });
    await vi.waitFor(() =>
      expect(screen.getByRole("region", { name: "Storage", hidden: true })).toHaveTextContent("8"),
    );
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Save" }));
    await screen.findByText(/changed since you loaded it/);
    expect(bodyOf(calls, "PUT", "/v1/catalogs/iceberg")).toMatchObject({ entity_version: 7 });
  });

  it("does not refetch the deleted catalog and drops its namespace lists", async () => {
    const user = userEvent.setup();
    const calls = stubCatalog({ "DELETE /v1/catalogs/iceberg": () => new Response(null, { status: 204 }) });
    const client = renderAt("/catalogs/iceberg");
    await screen.findByRole("link", { name: "retail" });
    await openAction(user, "Delete");
    await user.type(screen.getByLabelText(/to confirm/i), "iceberg");
    const before = calls.length;
    await user.click(screen.getByRole("button", { name: "Delete" }));
    await screen.findByText("catalogs list");
    const after = calls.slice(before).filter((call) => call.method === "GET");
    expect(after.map((call) => call.path)).not.toContain("/v1/catalogs/iceberg");
    expect(after.map((call) => call.path)).not.toContain("/v1/catalogs/iceberg/namespaces");
    expect(client.getQueryCache().findAll({ queryKey: ["catalog", "iceberg"] })).toHaveLength(0);
    expect(client.getQueryCache().findAll({ queryKey: ["namespaces", "iceberg"] })).toHaveLength(0);
  });

  it("tells the user that a dot is part of a namespace name", async () => {
    const user = userEvent.setup();
    stubCatalog();
    renderAt("/catalogs/iceberg");
    await screen.findByRole("link", { name: "retail" });
    await user.click(screen.getByRole("button", { name: "New namespace" }));
    expect(screen.getByRole("dialog")).toHaveTextContent(
      "A dot is part of the name. To nest a namespace, create it from its parent's page.",
    );
  });
});
