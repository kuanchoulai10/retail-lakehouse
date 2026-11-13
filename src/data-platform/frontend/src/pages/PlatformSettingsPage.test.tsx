import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import type { PlatformSettingsApiResponse } from "../api/generated/model";
import { stubCatalogApi } from "../test/catalogApiStub";
import { jsonResponse } from "../test/fixtures";
import { PlatformSettingsPage } from "./PlatformSettingsPage";

const PATH = "GET /v1/platform-settings";

const SETTINGS: PlatformSettingsApiResponse = {
  groups: [
    {
      key: "execution_capacity",
      title: "Execution capacity",
      items: [
        {
          key: "admission_limit",
          label: "Concurrent operations",
          value: 2,
          unit: "operations",
          description: "How many maintenance operations may run at the same time across the whole platform.",
        },
        {
          key: "maintenance_attempt_deadline_seconds",
          label: "Attempt time limit",
          value: 21_600,
          unit: "seconds",
          description: "How long one attempt of an operation may run before it is stopped and counted as failed.",
        },
      ],
    },
    {
      key: "compute_sizes",
      title: "Spark sizes",
      items: [
        {
          key: "compute_size_s_driver_memory",
          label: "S driver memory",
          value: "768m",
          unit: null,
          description: "The memory of the Spark driver when an operation runs at size S.",
        },
      ],
    },
    {
      key: "discovery",
      title: "Discovery",
      items: [
        {
          key: "discovery_interval_seconds",
          label: "Scan interval",
          value: 600,
          unit: "seconds",
          description: "How often discovery scans the catalogs for tables to manage.",
        },
      ],
    },
  ],
};

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/platform-settings"]}>
        <PlatformSettingsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("PlatformSettingsPage", () => {
  it("says the deployment sets these values and the console cannot change them", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse(SETTINGS) });
    renderPage();
    expect(await screen.findByRole("heading", { name: "Platform settings", level: 1 })).toBeInTheDocument();
    expect(
      screen.getByText("These values are set by the platform deployment; the console cannot change them."),
    ).toBeInTheDocument();
  });

  it("shows one panel per group, in the order the API gives", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse(SETTINGS) });
    renderPage();
    await screen.findByRole("region", { name: "Execution capacity" });
    const titles = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(titles).toEqual(["Execution capacity", "Spark sizes", "Discovery"]);
  });

  it("lists each setting's label, value with unit and description", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse(SETTINGS) });
    renderPage();
    const panel = await screen.findByRole("region", { name: "Execution capacity" });
    const facts = within(panel).getAllByRole("term").map((t) => t.textContent);
    expect(facts).toEqual(["Concurrent operations", "Attempt time limit"]);
    expect(within(panel).getByText("2 operations")).toBeInTheDocument();
    expect(
      within(panel).getByText("How many maintenance operations may run at the same time across the whole platform."),
    ).toBeInTheDocument();
  });

  it("reads seconds in the larger unit and keeps the exact count beside it", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse(SETTINGS) });
    renderPage();
    const panel = await screen.findByRole("region", { name: "Execution capacity" });
    expect(within(panel).getByText("6 h")).toBeInTheDocument();
    expect(within(panel).getByText("21,600 seconds")).toBeInTheDocument();
  });

  it("sets values in the monospace face", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse(SETTINGS) });
    renderPage();
    const panel = await screen.findByRole("region", { name: "Spark sizes" });
    expect(within(panel).getByText("768m")).toHaveClass("font-mono");
  });

  it("has no control that changes a setting", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse(SETTINGS) });
    renderPage();
    await screen.findByRole("region", { name: "Discovery" });
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("lets a keyboard reader focus each group, as the page has no other control", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse(SETTINGS) });
    renderPage();
    const panel = await screen.findByRole("region", { name: "Discovery" });
    expect(panel).toHaveAttribute("tabindex", "0");
  });

  it("holds a placeholder while the settings load", () => {
    stubCatalogApi({ [PATH]: () => new Promise<Response>(() => undefined) });
    renderPage();
    expect(screen.getByRole("status")).toHaveTextContent("Loading platform settings");
  });

  it("says when the settings cannot be loaded", async () => {
    stubCatalogApi({ [PATH]: () => jsonResponse({ detail: "scheduler down" }, 500) });
    renderPage();
    expect(await screen.findByText("Could not load platform settings: scheduler down")).toBeInTheDocument();
  });
});
