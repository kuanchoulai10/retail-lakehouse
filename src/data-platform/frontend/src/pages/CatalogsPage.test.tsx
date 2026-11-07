import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it } from "vitest";
import type { CatalogApiResponse } from "../api/catalogTypes";
import { bodyOf, callsTo, catalogFixture, stubCatalogApi } from "../test/catalogApiStub";
import { jsonResponse } from "../test/fixtures";
import { CatalogsPage } from "./CatalogsPage";

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/catalogs"]}>
        <Routes>
          <Route path="/catalogs" element={<CatalogsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function stubList() {
  let catalogs: CatalogApiResponse[] = [catalogFixture()];
  const calls = stubCatalogApi({
    "GET /v1/catalogs": () => jsonResponse(catalogs),
    "POST /v1/catalogs": (body) => {
      const created = catalogFixture({ name: (body as { name: string }).name });
      catalogs = [...catalogs, created];
      return jsonResponse(created, 201);
    },
  });
  return calls;
}

// These tests type whole forms, which takes seconds under a loaded parallel run.
describe("CatalogsPage", { timeout: 15_000 }, () => {
  it("catalogs page lists catalogs and creates one", async () => {
    const user = userEvent.setup();
    const calls = stubList();
    renderPage();
    const link = await screen.findByRole("link", { name: "iceberg" });
    expect(link).toHaveAttribute("href", "/catalogs/iceberg");
    expect(screen.getByRole("row", { name: /iceberg/ })).toHaveTextContent("INTERNAL");

    await user.click(screen.getByRole("button", { name: "New catalog" }));
    const dialog = screen.getByRole("dialog");
    await user.type(within(dialog).getByLabelText("Name"), "sales");
    await user.type(within(dialog).getByLabelText("Default base location"), "s3://warehouse/sales");
    await user.type(within(dialog).getByLabelText(/Allowed locations/), "s3://warehouse/sales/, s3://x/");
    await user.type(within(dialog).getByLabelText("Endpoint"), "http://rustfs:9000");
    await user.click(within(dialog).getByLabelText("Path style access"));
    await user.click(within(dialog).getByRole("button", { name: "Create" }));

    expect(await screen.findByRole("link", { name: "sales" })).toBeInTheDocument();
    const post = bodyOf(calls, "POST", "/v1/catalogs");
    expect(post).toEqual({
      name: "sales",
      type: "INTERNAL",
      default_base_location: "s3://warehouse/sales",
      storage_config: {
        storage_type: "S3",
        allowed_locations: ["s3://warehouse/sales/", "s3://x/"],
        endpoint: "http://rustfs:9000",
        path_style_access: true,
      },
    });
    expect(post).not.toHaveProperty("connection_config");
    expect(callsTo(calls, "GET", "/v1/catalogs")).toHaveLength(2);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("creates an external catalog with its connection and never echoes the secret", async () => {
    const user = userEvent.setup();
    const calls = stubList();
    renderPage();
    await screen.findByRole("link", { name: "iceberg" });
    await user.click(screen.getByRole("button", { name: "New catalog" }));
    const dialog = screen.getByRole("dialog");
    await user.type(within(dialog).getByLabelText("Name"), "remote");
    await user.type(within(dialog).getByLabelText("Default base location"), "s3://remote");
    await user.click(within(dialog).getByRole("combobox", { name: "Type" }));
    await user.click(await screen.findByRole("option", { name: "External" }));
    await user.click(within(dialog).getByRole("combobox", { name: "Connection type" }));
    await user.click(await screen.findByRole("option", { name: "Iceberg REST" }));
    await user.type(within(dialog).getByLabelText("URI"), "https://remote/api/catalog");
    await user.click(within(dialog).getByRole("combobox", { name: "Authentication" }));
    await user.click(await screen.findByRole("option", { name: "Bearer token" }));
    const token = within(dialog).getByLabelText("Bearer token");
    expect(token).toHaveAttribute("type", "password");
    await user.type(token, "s3cret");
    await user.click(within(dialog).getByRole("button", { name: "Create" }));

    await screen.findByRole("link", { name: "remote" });
    const post = bodyOf(calls, "POST", "/v1/catalogs");
    expect(post).toMatchObject({
      name: "remote",
      type: "EXTERNAL",
      connection_config: {
        connection_type: "REST",
        uri: "https://remote/api/catalog",
        authentication: { authentication_type: "BEARER", bearer_token: "s3cret" },
      },
    });
  });

  it("asks for a tenant id before creating an Azure catalog", async () => {
    const user = userEvent.setup();
    const calls = stubList();
    renderPage();
    await screen.findByRole("link", { name: "iceberg" });
    await user.click(screen.getByRole("button", { name: "New catalog" }));
    const dialog = screen.getByRole("dialog");
    await user.type(within(dialog).getByLabelText("Name"), "az");
    await user.type(within(dialog).getByLabelText("Default base location"), "abfss://c@a/x");
    await user.click(within(dialog).getByRole("combobox", { name: "Storage type" }));
    await user.click(await screen.findByRole("option", { name: "Azure" }));
    await user.click(within(dialog).getByRole("button", { name: "Create" }));
    expect(within(dialog).getByRole("alert")).toHaveTextContent("Tenant ID is required for Azure");
    expect(callsTo(calls, "POST", "/v1/catalogs")).toHaveLength(0);
  });

  it("shows the API error when catalogs cannot be loaded", async () => {
    stubCatalogApi({ "GET /v1/catalogs": () => jsonResponse({ detail: "polaris is down" }, 502) });
    renderPage();
    expect(await screen.findByText(/Could not load catalogs: polaris is down/)).toBeInTheDocument();
  });
});
