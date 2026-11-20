import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";
import { describe, expect, it } from "vitest";
import type {
  TableCurrentMetricsApiResponse,
  TableMetricTrendsApiResponse,
  TableMetricValuesApiResponse,
} from "../api/generated/model";
import { stubCatalogApi, type StubHandler } from "../test/catalogApiStub";
import { jsonResponse } from "../test/fixtures";
import { TableMetricsDashboard } from "./TableMetricsDashboard";

const CURRENT_PATH = "/v1/tables/uuid-orders/metrics/current";
const TRENDS_PATH = "/v1/tables/uuid-orders/metrics?range=";
const CARDS = ["Data files", "Data size", "Total rows", "Reducible files", "Snapshots", "Manifests"];
const SECTIONS = ["Files", "Size", "Rows", "Reducible files", "Manifests", "Snapshots"];

const METRICS: TableMetricValuesApiResponse = {
  data_files: 1174,
  position_delete_files: 12,
  equality_delete_files: 3,
  deletion_vectors: 2,
  data_records: 59_100_000,
  position_delete_records: 4200,
  equality_delete_records: 310,
  data_size_bytes: 4 * 1024 ** 3,
  reducible_files: 23,
  snapshots: 19,
  manifests: 9,
  manifests_size_bytes: 9 * 64 * 1024,
  manifest_added_entries: 40,
  manifest_existing_entries: 1100,
  manifest_deleted_entries: 6,
};

const VALUES = { ...METRICS, manifest_average_size_bytes: 64 * 1024, manifest_average_entries: 127 };

const CURRENT: TableCurrentMetricsApiResponse = { observed_at: "2026-11-20T09:58:00Z", metrics: METRICS };

function trends(range: string): TableMetricTrendsApiResponse {
  const at = (step: number) => new Date(Date.parse("2026-11-20T04:00:00Z") + step * 180_000).toISOString();
  return {
    time_range: range,
    start: at(0),
    end: at(2),
    step_seconds: 180,
    points: [
      { at: at(0), values: { data_files: null, snapshots: null } },
      { at: at(1), values: { ...VALUES, data_files: 1180, snapshots: 19 } },
      { at: at(2), values: { ...VALUES } },
    ],
  };
}

function Location() {
  const location = useLocation();
  return <p data-testid="location">{location.search}</p>;
}

function renderDashboard(
  routes: Record<string, StubHandler> = {},
  search = "",
  client = new QueryClient({ defaultOptions: { queries: { retry: false } } }),
) {
  const calls = stubCatalogApi({
    [`GET ${CURRENT_PATH}`]: () => jsonResponse(CURRENT),
    [`GET ${TRENDS_PATH}*`]: () => jsonResponse(trends("6h")),
    ...routes,
  });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/overview${search}`]}>
        <TableMetricsDashboard tableUuid="uuid-orders" />
        <Location />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return calls;
}

function cards(): HTMLElement[] {
  return screen.getAllByRole("group", { name: new RegExp(`^(${CARDS.join("|")})$`) });
}

function trendRequests(calls: { path: string }[]): string[] {
  return calls.filter((call) => call.path.startsWith(TRENDS_PATH)).map((call) => call.path);
}

describe("TableMetricsDashboard", () => {
  it("shows the six cards in order with their formatted values and the trend's delta", async () => {
    renderDashboard();
    await screen.findByText("1,174");
    expect(cards().map((card) => card.querySelector("p")?.textContent)).toEqual(CARDS);
    const values = cards().map((card) => card.querySelectorAll("p")[1]?.textContent);
    expect(values).toEqual(["1,174", "4.0 GB", "59,100,000", "23", "19", "9"]);
    const dataFiles = within(screen.getByRole("group", { name: "Data files" }));
    expect(await dataFiles.findByText("−6 in 6h")).toBeInTheDocument();
    expect(within(screen.getByRole("group", { name: "Snapshots" })).getByText("No change in 6h")).toBeInTheDocument();
  });

  it("names the size card and chart after data files, whose bytes they count", async () => {
    renderDashboard();
    await screen.findByText("1,174");
    await waitFor(() => expect(screen.getAllByRole("img", { name: "Data size over the last 6 hours" })).toHaveLength(2));
    expect(screen.queryByText(/Total size/)).toBeNull();
  });

  it("says when the cards were measured, beside the range picker", async () => {
    const observedAt = new Date(Date.now() - 5 * 60_000).toISOString();
    renderDashboard({ [`GET ${CURRENT_PATH}`]: () => jsonResponse({ ...CURRENT, observed_at: observedAt }) });
    expect(await screen.findByText("Measured 5 min ago")).toBeInTheDocument();
  });

  it("says nothing about when the cards were measured before the first reconciliation", async () => {
    renderDashboard({ [`GET ${CURRENT_PATH}`]: () => jsonResponse({ observed_at: null, metrics: null }) });
    await screen.findByText("Metrics appear after the table's next reconciliation.");
    expect(screen.queryByText(/^Measured/)).toBeNull();
  });

  it("drops the cards' delta and sparkline when the trends fail after a good answer", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    let failing = false;
    renderDashboard(
      {
        [`GET ${TRENDS_PATH}*`]: () =>
          failing ? jsonResponse({ detail: "Prometheus is down" }, 502) : jsonResponse(trends("6h")),
      },
      "",
      client,
    );
    const dataFiles = within(await screen.findByRole("group", { name: "Data files" }));
    expect(await dataFiles.findByText("−6 in 6h")).toBeInTheDocument();
    expect(dataFiles.getByRole("img", { name: "Data files over the last 6 hours" })).toBeInTheDocument();
    failing = true;
    await client.refetchQueries();
    await waitFor(() => expect(screen.getAllByRole("alert")).toHaveLength(7));
    expect(dataFiles.queryByText("−6 in 6h")).toBeNull();
    expect(dataFiles.queryByRole("img")).toBeNull();
    expect(dataFiles.getByText("1,174")).toBeInTheDocument();
  });

  it("holds six sections, one per topic", async () => {
    renderDashboard();
    await screen.findByText("1,174");
    expect(screen.getAllByRole("region").map((region) => region.querySelector("h2")?.textContent)).toEqual(SECTIONS);
  });

  it("shows a dash on every card and says when metrics appear, before the first reconciliation", async () => {
    renderDashboard({ [`GET ${CURRENT_PATH}`]: () => jsonResponse({ observed_at: null, metrics: null }) });
    expect(await screen.findByText("Metrics appear after the table's next reconciliation.")).toBeInTheDocument();
    expect(cards().map((card) => card.querySelectorAll("p")[1]?.textContent)).toEqual(CARDS.map(() => "—"));
  });

  it("says the trends are unavailable on every chart, while the cards keep their values", async () => {
    renderDashboard({ [`GET ${TRENDS_PATH}*`]: () => jsonResponse({ detail: "Prometheus is down" }, 502) });
    await waitFor(() => expect(screen.getAllByRole("alert")).toHaveLength(7));
    for (const alert of screen.getAllByRole("alert")) {
      expect(alert).toHaveTextContent("Trends unavailable: Prometheus is down");
    }
    expect(await within(screen.getByRole("group", { name: "Data files" })).findByText("1,174")).toBeInTheDocument();
  });

  it("says the current metrics are unavailable, shows a dash on every card, and still draws the trends", async () => {
    renderDashboard({ [`GET ${CURRENT_PATH}`]: () => jsonResponse({ detail: "database down" }, 502) });
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load the current metrics: database down");
    expect(cards().map((card) => card.querySelectorAll("p")[1]?.textContent)).toEqual(CARDS.map(() => "—"));
    await waitFor(() => expect(screen.getAllByRole("img", { name: / over the last 6 hours$/ })).toHaveLength(7));
    expect(screen.getAllByRole("alert")).toHaveLength(1);
  });

  it("asks for the last 6 hours by default and keeps the url clean", async () => {
    const calls = renderDashboard();
    await screen.findByText("1,174");
    await waitFor(() => expect(trendRequests(calls)).toEqual([`${TRENDS_PATH}6h`]));
    expect(screen.getByRole("radio", { name: "Last 6 hours" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByTestId("location")).toHaveTextContent(/^$/);
  });

  it("choosing 1h asks for the last hour and puts the range in the url", async () => {
    const user = userEvent.setup();
    const calls = renderDashboard();
    await screen.findByText("1,174");
    await user.click(screen.getByRole("radio", { name: "Last 1 hour" }));
    await waitFor(() => expect(trendRequests(calls)).toContain(`${TRENDS_PATH}1h`));
    expect(screen.getByTestId("location")).toHaveTextContent("?range=1h");
    expect(calls.filter((call) => call.path === CURRENT_PATH)).toHaveLength(1);
    await user.click(screen.getByRole("radio", { name: "Last 6 hours" }));
    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent(/^$/));
  });

  it("reads the range from the url", async () => {
    const calls = renderDashboard({}, "?range=3h");
    await waitFor(() => expect(trendRequests(calls)).toEqual([`${TRENDS_PATH}3h`]));
  });

  it("an unknown range in the url asks for the last 6 hours", async () => {
    const calls = renderDashboard({}, "?range=2d");
    await waitFor(() => expect(trendRequests(calls)).toEqual([`${TRENDS_PATH}6h`]));
  });
});
