import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { expectNoHorizontalPageScroll } from "../../stories/assertions";
import { Breadcrumbs } from "./Breadcrumbs";

const meta = {
  title: "Components/Breadcrumbs",
  component: Breadcrumbs,
  args: {
    items: [
      { label: "Tables", href: "/tables" },
      { label: "sales", href: "/tables/sales" },
      { label: "orders" },
    ],
    renderLink: (item, children) => <a href={`#${item.href}`}>{children}</a>,
  },
  parameters: {
    docs: {
      description: {
        component:
          "Expanded departs from Serendie only in text size (expanded typography). Long labels " +
          "truncate and carry the full text in a title.",
      },
    },
  },
} satisfies Meta<typeof Breadcrumbs>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("navigation", { name: "Breadcrumb" })).toBeInTheDocument();
    await expect(canvas.getAllByRole("link")).toHaveLength(2);
    await expect(canvas.getByText("orders").parentElement).toHaveAttribute("aria-current", "page");
  },
};

export const LongLabels: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  args: {
    items: [
      { label: "Tables", href: "/tables" },
      { label: "a_very_long_namespace_name_that_keeps_going_and_going", href: "/n" },
      { label: "an_equally_long_table_name_that_should_be_truncated_somewhere" },
    ],
  },
  play: async ({ canvasElement }) => {
    const long = within(canvasElement).getByText(
      "an_equally_long_table_name_that_should_be_truncated_somewhere",
    );
    await expect(long).toHaveAttribute(
      "title",
      "an_equally_long_table_name_that_should_be_truncated_somewhere",
    );
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
