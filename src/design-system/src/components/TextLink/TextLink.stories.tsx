import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import { TextLink } from "./TextLink";

const meta = {
  title: "Components/TextLink",
  component: TextLink,
  args: {
    asChild: true,
    children: <a href="#/tables/sales/orders">sales.orders</a>,
  },
  parameters: {
    docs: {
      description: {
        component:
          "A link in the theme's primary colour, as Serendie colours its links (Breadcrumbs). " +
          "Standalone links (table cells, lists) underline on hover; `inline` links inside a " +
          "sentence stay underlined so they do not rely on colour alone. Pass the router's " +
          "link with `asChild`.",
      },
    },
  },
} satisfies Meta<typeof TextLink>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Standalone: Story = {
  play: async ({ canvasElement }) => {
    const link = within(canvasElement).getByRole("link", { name: "sales.orders" });
    await expect(link).toHaveClass("text-primary");
    await expect(getComputedStyle(link).textDecorationLine).toBe("none");
    await userEvent.tab();
    await expect(link).toHaveFocus();
    await expect(getComputedStyle(link).outlineStyle).toBe("solid");
  },
};

export const Inline: Story = {
  args: { inline: true, children: <a href="#/discovery-rules">Add a discovery rule</a> },
  render: (args) => (
    <p className="type-body-medium text-on-surface">
      No tables yet. <TextLink {...args} /> to find some.
    </p>
  ),
  play: async ({ canvasElement }) => {
    const link = within(canvasElement).getByRole("link", { name: "Add a discovery rule" });
    await expect(link).toHaveClass("text-primary");
    await expect(getComputedStyle(link).textDecorationLine).toBe("underline");
  },
};
