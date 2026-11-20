import type { Meta, StoryObj } from "@storybook/react-vite";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { expect, userEvent, waitFor, within } from "storybook/test";
import {
  getGetTableCurrentMetricsMockHandler,
  getGetTableMetricTrendsMockHandler,
} from "@/api/generated/tables/tables.msw";
import { apiError } from "@/stories/apiError";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";
import { ORDERS_METRIC_TRENDS, ORDERS_UUID } from "@/stories/storyData";
import { TableMetricsDashboard } from "./TableMetricsDashboard";

const CARDS = ["Data files", "Data size", "Total rows", "Reducible files", "Snapshots", "Manifests"];
const CHARTS = 7;

const meta = {
  title: "Components/Table metrics dashboard",
  component: TableMetricsDashboard,
  args: { tableUuid: ORDERS_UUID },
  decorators: [
    (Story) => (
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={["/overview"]}>
          <div className="bg-surface p-4">
            <Story />
          </div>
        </MemoryRouter>
      </QueryClientProvider>
    ),
  ],
  beforeEach({ msw }) {
    msw.use(...lakehouseHandlers());
  },
} satisfies Meta<typeof TableMetricsDashboard>;

export default meta;
type Story = StoryObj<typeof meta>;

// The charts that take focus (sparklines do not), once every one has drawn.
async function focusableCharts(canvasElement: HTMLElement): Promise<SVGElement[]> {
  return waitFor(() => {
    const charts = Array.from(canvasElement.querySelectorAll<SVGElement>('svg.recharts-surface[tabindex="0"]'));
    expect(charts).toHaveLength(CHARTS);
    return charts;
  });
}

async function tooltipOf(chart: SVGElement): Promise<HTMLElement> {
  return waitFor(() => {
    const found = chart.closest(".recharts-wrapper")?.querySelector<HTMLElement>("[data-chart-tooltip]");
    expect(found).toBeTruthy();
    return found as HTMLElement;
  });
}

// Tab reaches the range picker, whose arrows move between 1h, 3h and 6h and whose Enter or Space
// chooses; then Tab reaches each chart in turn, and its arrows move the tooltip from point to point.
export const Keyboard: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      (await canvas.findAllByRole("group", { name: new RegExp(`^(${CARDS.join("|")})$`) })).length,
    ).toBe(CARDS.length);
    await expect(await canvas.findByText("1,174")).toBeVisible();
    await expect(canvas.getByText(/^Measured /)).toBeVisible();
    await focusableCharts(canvasElement);
    const picker = canvas.getByRole("radiogroup", { name: "Time range" });
    const [oneHour, threeHours, sixHours] = within(picker).getAllByRole("radio") as [HTMLElement, HTMLElement, HTMLElement];
    await userEvent.tab();
    await expect(sixHours).toHaveFocus();
    await userEvent.keyboard("{ArrowLeft}");
    await expect(threeHours).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    await expect(threeHours).toHaveAttribute("aria-checked", "true");
    await userEvent.keyboard("{ArrowLeft}");
    await expect(oneHour).toHaveFocus();
    await userEvent.keyboard(" ");
    await expect(oneHour).toHaveAttribute("aria-checked", "true");
    await expect(await canvas.findByRole("img", { name: "Data and delete files over the last hour" })).toBeVisible();
    const charts = await focusableCharts(canvasElement);
    for (const chart of charts) {
      await userEvent.tab();
      await expect(chart).toHaveFocus();
      const tooltip = await tooltipOf(chart);
      const first = tooltip.textContent;
      await expect(tooltip).toHaveTextContent(/\d{2}:\d{2}:\d{2}/);
      await userEvent.keyboard("{ArrowRight}");
      await waitFor(() => expect(tooltip.textContent).not.toBe(first));
      await userEvent.keyboard("{ArrowLeft}");
      await waitFor(() => expect(tooltip.textContent).toBe(first));
    }
  },
};

export const NotReconciledYet: Story = {
  beforeEach({ msw }) {
    msw.use(
      getGetTableCurrentMetricsMockHandler({ observed_at: null, metrics: null }),
      getGetTableMetricTrendsMockHandler({
        ...ORDERS_METRIC_TRENDS,
        points: ORDERS_METRIC_TRENDS.points.map((point) => ({ at: point.at, values: {} })),
      }),
    );
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("Metrics appear after the table's next reconciliation.")).toBeVisible();
    await expect(canvas.queryByText(/^Measured /)).toBeNull();
    await waitFor(() => expect(canvas.getAllByText("No data in this time range")).toHaveLength(CHARTS));
    for (const label of CARDS) {
      await expect(canvas.getByRole("group", { name: label })).toHaveTextContent("—");
    }
  },
};

export const TrendsUnavailable: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("get", "/v1/tables/:tableUuid/metrics", "Prometheus did not answer"));
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await waitFor(() => expect(canvas.getAllByRole("alert")).toHaveLength(CHARTS));
    for (const alert of canvas.getAllByRole("alert")) {
      await expect(alert).toHaveTextContent("Trends unavailable: Prometheus did not answer");
    }
    await expect(canvas.getByRole("group", { name: "Data files" })).toHaveTextContent("1,174");
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await focusableCharts(canvasElement);
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
