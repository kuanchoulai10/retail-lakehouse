import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import { expectFocusRing, expectNoHorizontalPageScroll } from "../../stories/assertions";
import { createDataTableColumnHelper } from "./createDataTableColumnHelper";
import { DataTable } from "./DataTable";

type Row = { id: string; name: string; status: string; files: number };

const rows: Row[] = [
  { id: "1", name: "sales.orders", status: "active", files: 1204 },
  { id: "2", name: "sales.customers", status: "paused", files: 88 },
  { id: "3", name: "ops.events", status: "active", files: 5 },
];

const helper = createDataTableColumnHelper<Row>();
const columns = helper.columns([
  helper.accessor("name", { header: "Name", sortFn: "text" }),
  helper.accessor("status", { header: "Status", sortFn: "text" }),
  helper.accessor("files", { header: "Files", sortFn: "basic", }),
]);

type WideRow = Record<string, string>;
const wideHelper = createDataTableColumnHelper<WideRow>();
const wideColumns = wideHelper.columns(
  Array.from({ length: 12 }, (_, index) =>
    wideHelper.accessor(`c${index}`, { header: `Column ${index + 1}`, sortFn: "text" }),
  ),
);
const wideRows: WideRow[] = Array.from({ length: 3 }, (_, row) =>
  Object.fromEntries(Array.from({ length: 12 }, (_, col) => [`c${col}`, `r${row}-value-${col}`])),
);

const meta = {
  title: "Components/DataTable",
  component: DataTable,
  args: { caption: "Tables", columns: [], data: [] },
  parameters: {
    docs: {
      description: {
        component:
          "Expanded departs from Serendie: rows are 36px high (44px below 768px). Sorting is by " +
          "header buttons that set aria-sort. The table scrolls inside its own container with a " +
          "sticky first column, so the page never scrolls sideways.",
      },
    },
  },
} satisfies Meta<typeof DataTable>;

export default meta;

type Story = StoryObj<typeof meta>;

function firstColumnNames(root: HTMLElement): string[] {
  return Array.from(root.querySelectorAll("tbody tr")).map(
    (row) => row.querySelector("td")?.textContent ?? "",
  );
}
export const Sortable: Story = {
  render: () => (
    <DataTable<Row>
      caption="Tables"
      columns={columns}
      data={rows}
      getRowId={(row) => row.id}
    />
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const header = canvas.getByRole("columnheader", { name: "Name" });
    const button = within(header).getByRole("button", { name: "Name" });
    await expect(header).toHaveAttribute("aria-sort", "none");
    await userEvent.tab();
    await expectFocusRing(canvas.getByRole("region", { name: "Tables" }));
    await userEvent.tab();
    await expectFocusRing(button);
    await userEvent.keyboard("{Enter}");
    await expect(header).toHaveAttribute("aria-sort", "ascending");
    await expect(firstColumnNames(canvasElement)).toEqual(["ops.events", "sales.customers", "sales.orders"]);
    await userEvent.keyboard("{Enter}");
    await expect(header).toHaveAttribute("aria-sort", "descending");
    await expect(firstColumnNames(canvasElement)).toEqual(["sales.orders", "sales.customers", "ops.events"]);
    await userEvent.keyboard(" ");
    await expect(header).toHaveAttribute("aria-sort", "none");
  },
};

export const InitialSorting: Story = {
  render: () => (
    <DataTable<Row>
      caption="Tables"
      columns={columns}
      data={rows}
      initialSorting={[{ id: "files", desc: true }]}
    />
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("columnheader", { name: "Files" })).toHaveAttribute(
      "aria-sort",
      "descending",
    );
    await expect(firstColumnNames(canvasElement)[0]).toBe("sales.orders");
  },
};

export const Empty: Story = {
  render: () => (
    <DataTable<Row>
      caption="Tables"
      columns={columns}
      data={[]}
      emptyState={<span>No tables match.</span>}
    />
  ),
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText("No tables match.")).toBeVisible();
  },
};

export const WidePhone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  render: () => (
    <DataTable<WideRow> caption="Wide table" columns={wideColumns} data={wideRows} />
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const scroller = canvas.getByRole("region", { name: "Wide table" });
    await expect(scroller.scrollWidth).toBeGreaterThan(scroller.clientWidth);
    await expectNoHorizontalPageScroll(canvasElement);
    const firstCell = canvas.getAllByRole("row")[1]!.querySelector("td") as HTMLElement;
    await expect(getComputedStyle(firstCell).position).toBe("sticky");
    const firstHead = canvas.getAllByRole("columnheader")[0] as HTMLElement;
    await expect(getComputedStyle(firstHead).position).toBe("sticky");
  },
};

const wideColumnsWithHiddenHeader = [
  ...wideColumns,
  wideHelper.display({
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: () => <button type="button">Delete</button>,
  }),
];

export const WidePhoneWithHiddenHeader: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  render: () => (
    <DataTable<WideRow>
      caption="Wide table with actions"
      columns={wideColumnsWithHiddenHeader}
      data={wideRows}
    />
  ),
  play: async ({ canvasElement }) => {
    const scroller = within(canvasElement).getByRole("region", { name: "Wide table with actions" });
    await expect(scroller.scrollWidth).toBeGreaterThan(scroller.clientWidth);
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
