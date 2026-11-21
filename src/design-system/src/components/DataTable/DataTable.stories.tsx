import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { expect, fn, userEvent, waitFor, within } from "storybook/test";
import {
  expectFocusRing,
  expectNoHorizontalPageScroll,
  portalQueries,
  resolvedColor,
} from "../../stories/assertions";
import { Drawer } from "../Drawer/Drawer";
import { createDataTableColumnHelper } from "./createDataTableColumnHelper";
import { DataTable, type DataTableProps } from "./DataTable";

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
          "sticky first column, so the page never scrolls sideways. With renderDetail, each row " +
          "opens a full-width detail row from a toggle in its first cell or a click on the row. " +
          "With onOpenRow, a row opens somewhere else, such as a side panel, from a button in its " +
          "first cell or a click on the row; openRowId marks the row whose panel is open.",
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

const plainColumns = helper.columns([
  helper.accessor("name", { header: "Name", enableSorting: false }),
  helper.accessor("status", { header: "Status", enableSorting: false }),
  helper.accessor("files", { header: "Files", enableSorting: false }),
]);

const renderDetail = (row: Row) => <p>{`Detail of ${row.name}`}</p>;

export const ExpandableRows: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  render: () => (
    <DataTable<Row>
      caption="Expandable tables"
      columns={plainColumns}
      data={rows}
      getRowId={(row) => row.id}
      getRowLabel={(row) => row.name}
      renderDetail={renderDetail}
    />
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.tab();
    await userEvent.tab();
    const toggle = canvas.getByRole("button", { name: "Expand sales.orders" });
    await expectFocusRing(toggle);
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    await expect(canvas.queryByText("Detail of sales.orders")).toBeNull();
    await userEvent.keyboard("{Enter}");
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    await expect(toggle).toHaveAccessibleName("Collapse sales.orders");
    const detail = canvas.getByText("Detail of sales.orders");
    await expect(detail).toBeVisible();
    await expect(detail.closest("td")).toHaveAttribute("colspan", "3");
    await userEvent.keyboard("{Enter}");
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    await expect(canvas.queryByText("Detail of sales.orders")).toBeNull();
  },
};

export const ExpandableRowsByRowClick: Story = {
  render: ExpandableRows.render,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByText("sales.customers"));
    await expect(canvas.getByText("Detail of sales.customers")).toBeVisible();
    await userEvent.click(canvas.getByRole("button", { name: "Collapse sales.customers" }));
    await expect(canvas.queryByText("Detail of sales.customers")).toBeNull();
  },
};

const lettered: Row[] = [
  { id: "a", name: "sales.orders", status: "active", files: 1204 },
  { id: "b", name: "sales.customers", status: "paused", files: 88 },
  { id: "c", name: "ops.events", status: "active", files: 5 },
];

export const InitialExpanded: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  render: () => (
    <DataTable<Row>
      caption="Initially expanded tables"
      columns={plainColumns}
      data={lettered}
      getRowId={(row) => row.id}
      getRowLabel={(row) => row.name}
      renderDetail={renderDetail}
      initialExpandedRowIds={["b", "unknown"]}
    />
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const opened = canvas.getByRole("button", { name: "Collapse sales.customers" });
    await expect(opened).toHaveAttribute("aria-expanded", "true");
    await expect(canvas.getByText("Detail of sales.customers")).toBeVisible();
    await expect(canvas.getByRole("button", { name: "Expand sales.orders" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    await expect(canvas.getByRole("button", { name: "Expand ops.events" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    await expect(canvas.getAllByText(/^Detail of /)).toHaveLength(1);
    await expect(canvas.getAllByRole("row")).toHaveLength(5);
  },
};

const wideDetail = (row: WideRow) => <p>{`Detail of ${row.c0}`}</p>;

export const ExpandableWidePhone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  render: () => (
    <DataTable<WideRow>
      caption="Wide expandable table"
      columns={wideColumns}
      data={wideRows}
      getRowLabel={(row) => row.c0 ?? ""}
      renderDetail={wideDetail}
    />
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "Expand r0-value-0" }));
    await expect(canvas.getByText("Detail of r0-value-0")).toBeVisible();
    const firstCell = canvas.getAllByRole("row")[1]!.querySelector("td") as HTMLElement;
    await expect(getComputedStyle(firstCell).position).toBe("sticky");
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

const onOpen = fn();
const interactiveColumns = helper.columns([
  helper.accessor("name", { header: "Name", enableSorting: false }),
  helper.accessor("status", {
    header: "Status",
    enableSorting: false,
    cell: (info) => (
      <a href={`#${info.getValue()}`} onClick={(event) => event.preventDefault()}>
        {info.getValue()}
      </a>
    ),
  }),
  helper.accessor("files", {
    header: "Files",
    enableSorting: false,
    cell: (info) => (
      <span className="inline-flex gap-2">
        <button type="button" onClick={onOpen}>
          Open
        </button>
        <span role="button" tabIndex={0}>
          {`${info.getValue()} files`}
        </span>
        <input aria-label={`Note for ${info.row.original.name}`} />
      </span>
    ),
  }),
]);

export const RowClickIgnoresControlsAndSelection: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  render: () => (
    <DataTable<Row>
      caption="Tables with controls"
      columns={interactiveColumns}
      data={rows}
      getRowId={(row) => row.id}
      getRowLabel={(row) => row.name}
      renderDetail={renderDetail}
    />
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const detail = () => canvas.queryByText("Detail of sales.orders");
    const [activeLink] = canvas.getAllByRole("link", { name: "active" });
    await userEvent.click(activeLink!);
    await expect(detail()).toBeNull();
    const [open] = canvas.getAllByRole("button", { name: "Open" });
    await userEvent.click(open!);
    await expect(onOpen).toHaveBeenCalled();
    await expect(detail()).toBeNull();
    await userEvent.click(canvas.getByRole("button", { name: "1204 files" }));
    await expect(detail()).toBeNull();
    await userEvent.click(canvas.getByRole("textbox", { name: "Note for sales.orders" }));
    await expect(detail()).toBeNull();

    const nameCell = canvas.getByText("sales.orders");
    const selection = window.getSelection()!;
    const range = document.createRange();
    range.selectNodeContents(nameCell);
    selection.removeAllRanges();
    selection.addRange(range);
    nameCell.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await expect(detail()).toBeNull();

    selection.removeAllRanges();
    await userEvent.click(nameCell);
    await expect(detail()).toBeVisible();
  },
};

function OpenRowInPanelHarness() {
  const [openId, setOpenId] = useState<string | null>(null);
  const open = rows.find((row) => row.id === openId) ?? null;
  return (
    <div className="flex items-start gap-4 p-4">
      <DataTable<Row>
        caption="Tables opening in a panel"
        columns={plainColumns}
        data={rows}
        getRowId={(row) => row.id}
        getRowLabel={(row) => row.name}
        onOpenRow={(row) => setOpenId(row.id)}
        openRowId={openId}
        className="flex-1"
      />
      <Drawer
        title={open?.name ?? "Table"}
        contentKey={openId ?? undefined}
        isOpen={open !== null}
        onOpenChange={(isOpen) => {
          if (!isOpen) setOpenId(null);
        }}
        modal={false}
      >
        {open ? `Details of ${open.name}` : null}
      </Drawer>
    </div>
  );
}

export const OpenRowInPanel: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  render: () => <OpenRowInPanelHarness />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const first = canvas.getByRole("button", { name: "Open sales.orders" });
    const second = canvas.getByRole("button", { name: "Open sales.customers" });
    await expect(first).toHaveAttribute("aria-haspopup", "dialog");
    await expect(first).toHaveAttribute("aria-expanded", "false");
    await userEvent.tab();
    await userEvent.tab();
    await expectFocusRing(first);
    await userEvent.keyboard("{Enter}");
    await expect(first).toHaveAttribute("aria-expanded", "true");
    const heading = await portalQueries(canvasElement).findByRole("heading", { name: "sales.orders" });
    await waitFor(() => expect(heading).toHaveFocus());
    await expect(first.closest("tr")).toHaveClass("bg-inverse-primary");
    const selected = resolvedColor("inverse-primary", canvasElement);
    await expect(getComputedStyle(first.closest("td")!).backgroundColor).toBe(selected);

    await userEvent.click(canvas.getByText("sales.customers"));
    await expect(second).toHaveAttribute("aria-expanded", "true");
    await expect(first).toHaveAttribute("aria-expanded", "false");
    await expect(first.closest("tr")).not.toHaveClass("bg-inverse-primary");
    await expect(getComputedStyle(first.closest("td")!).backgroundColor).not.toBe(selected);
    await expect(getComputedStyle(second.closest("td")!).backgroundColor).toBe(selected);
    const switched = await portalQueries(canvasElement).findByRole("heading", { name: "sales.customers" });
    await waitFor(() => expect(switched).toHaveFocus());

    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(portalQueries(canvasElement).queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(second).toHaveFocus());
    await expect(second).toHaveAttribute("aria-expanded", "false");
  },
};

const onOpenRowSpy = fn();
const openRowColumns = helper.columns([
  helper.accessor("name", { header: "Name", enableSorting: false }),
  helper.accessor("status", {
    header: "Status",
    enableSorting: false,
    cell: (info) => (
      <span className="inline-flex gap-2">
        <a href={`#${info.getValue()}`} onClick={(event) => event.preventDefault()}>
          {info.getValue()}
        </a>
        <button type="button">{`Note ${info.row.original.id}`}</button>
      </span>
    ),
  }),
]);

export const OpenRowClickRules: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  render: () => (
    <DataTable<Row>
      caption="Tables with an open spy"
      columns={openRowColumns}
      data={rows}
      getRowId={(row) => row.id}
      getRowLabel={(row) => row.name}
      onOpenRow={onOpenRowSpy}
    />
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    onOpenRowSpy.mockClear();
    await userEvent.click(canvas.getAllByRole("link", { name: "active" })[0]!);
    await userEvent.click(canvas.getByRole("button", { name: "Note 1" }));
    await expect(onOpenRowSpy).toHaveBeenCalledTimes(0);

    const nameCell = canvas.getByText("sales.orders");
    const modified = userEvent.setup();
    for (const key of ["Meta", "Control", "Shift", "Alt"]) {
      await modified.keyboard(`{${key}>}`);
      await modified.click(nameCell);
      await modified.keyboard(`{/${key}}`);
    }
    await expect(onOpenRowSpy).toHaveBeenCalledTimes(0);

    const selection = window.getSelection()!;
    const range = document.createRange();
    range.selectNodeContents(nameCell);
    selection.removeAllRanges();
    selection.addRange(range);
    nameCell.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await expect(onOpenRowSpy).toHaveBeenCalledTimes(0);
    selection.removeAllRanges();

    await userEvent.click(canvas.getByRole("button", { name: "Open sales.orders" }));
    await expect(onOpenRowSpy).toHaveBeenCalledTimes(1);
    await expect(onOpenRowSpy).toHaveBeenLastCalledWith(rows[0]);

    onOpenRowSpy.mockClear();
    await userEvent.click(canvas.getByText("sales.customers"));
    await expect(onOpenRowSpy).toHaveBeenCalledTimes(1);
    await expect(onOpenRowSpy).toHaveBeenLastCalledWith(rows[1]);
    await expect(canvas.getByRole("button", { name: "Open sales.customers" })).toHaveFocus();
  },
};

// A row either expands or opens: tsc fails here if DataTableProps stops refusing both.
// @ts-expect-error renderDetail and onOpenRow are never passed together
const bothProps: DataTableProps<Row> = { caption: "Both", columns: plainColumns, data: rows, renderDetail, onOpenRow: onOpen };
void bothProps;
