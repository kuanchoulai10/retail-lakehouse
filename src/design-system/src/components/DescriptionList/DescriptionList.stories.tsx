import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { expectNoHorizontalPageScroll } from "../../stories/assertions";
import { TextLink } from "../TextLink/TextLink";
import { DescriptionList } from "./DescriptionList";

const items = [
  { term: "Table", description: "sales.orders" },
  { term: "Operation", description: "rewrite_data_files" },
  { term: "Trigger", description: "Scheduled" },
  {
    term: "Reconciliation",
    description: (
      <TextLink asChild>
        <a href="#/reconciliations/rc-1">rc-1</a>
      </TextLink>
    ),
  },
  { term: "Created", description: "2026-11-21 09:30" },
];

const meta = {
  title: "Components/DescriptionList",
  component: DescriptionList,
  args: { items },
  parameters: {
    docs: {
      description: {
        component:
          "Terms and their values, for the facts of one record such as a side panel. Serendie has " +
          "no such component. Not interactive: a description may hold a link, and the list adds " +
          "nothing to it. At 768px and wider the terms sit in a column beside the values; below " +
          "that each term stacks above its value, so a long value never scrolls the page sideways.",
      },
    },
  },
} satisfies Meta<typeof DescriptionList>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getAllByRole("term")).toHaveLength(5);
    await expect(canvas.getAllByRole("definition")).toHaveLength(5);
    await expect(canvas.getByRole("link", { name: "rc-1" })).toHaveAttribute(
      "href",
      "#/reconciliations/rc-1",
    );
    const term = canvas.getByText("Table");
    const description = canvas.getByText("sales.orders");
    await expect(description.getBoundingClientRect().left).toBeGreaterThan(
      term.getBoundingClientRect().right - 1,
    );
  },
};

const where = "x".repeat(400);

export const LongValues: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  args: {
    items: [
      { term: "Operation", description: "rewrite_data_files" },
      { term: "where", description: where },
    ],
  },
  render: (args) => (
    <div className="w-96">
      <DescriptionList {...args} />
    </div>
  ),
  play: async ({ canvasElement }) => {
    const list = canvasElement.querySelector("dl") as HTMLElement;
    await expect(list.scrollWidth).toBeLessThanOrEqual(list.clientWidth);
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  args: {
    items: [...items, { term: "where", description: where }],
  },
  play: async ({ canvasElement }) => {
    const terms = Array.from(canvasElement.querySelectorAll("dt"));
    const descriptions = Array.from(canvasElement.querySelectorAll("dd"));
    await expect(terms).toHaveLength(6);
    for (const [index, term] of terms.entries()) {
      await expect(descriptions[index]!.getBoundingClientRect().top).toBeGreaterThanOrEqual(
        term.getBoundingClientRect().bottom,
      );
    }
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
