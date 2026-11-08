import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { expectNoHorizontalPageScroll } from "../../stories/assertions";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./Table";

const meta = {
  title: "Components/Table",
  component: Table,
  parameters: {
    docs: {
      description: {
        component:
          "Expanded departs from Serendie: rows are 36px high (44px below 768px and under a " +
          "coarse pointer). Numeric cells are right-aligned with tabular figures.",
      },
    },
  },
} satisfies Meta<typeof Table>;

export default meta;

type Story = StoryObj<typeof meta>;

function Rows() {
  return (
    <>
      <TableHeader>
        <TableRow>
          <TableHead>Table</TableHead>
          <TableHead numeric>Files</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow>
          <TableCell>sales.orders</TableCell>
          <TableCell numeric>1,204</TableCell>
        </TableRow>
        <TableRow>
          <TableCell>sales.customers</TableCell>
          <TableCell numeric>88</TableCell>
        </TableRow>
      </TableBody>
    </>
  );
}

export const Default: Story = {
  render: () => (
    <Table aria-label="Tables">
      <Rows />
    </Table>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getAllByRole("row")).toHaveLength(3);
    const cell = canvas.getByRole("cell", { name: "1,204" });
    await expect(getComputedStyle(cell).textAlign).toBe("right");
    await expect(getComputedStyle(cell).fontVariantNumeric).toContain("tabular-nums");
  },
};

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  render: () => (
    <Table aria-label="Tables">
      <Rows />
    </Table>
  ),
  play: async ({ canvasElement }) => {
    await expectNoHorizontalPageScroll(canvasElement);
    const row = within(canvasElement).getAllByRole("row")[1] as HTMLElement;
    await expect(row.getBoundingClientRect().height).toBeGreaterThanOrEqual(44);
  },
};
