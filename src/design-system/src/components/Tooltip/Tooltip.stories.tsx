import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, waitFor, within } from "storybook/test";
import { SerendieSymbolTrash } from "../../icons";
import { expectNoHorizontalPageScroll } from "../../stories/assertions";
import { IconButton } from "../IconButton/IconButton";
import { Tooltip, TooltipProvider } from "./Tooltip";

const meta = {
  title: "Components/Tooltip",
  component: Tooltip,
  args: {
    content: "Delete rule",
    children: <IconButton aria-label="Delete rule" icon={<SerendieSymbolTrash aria-hidden="true" />} />,
  },
  decorators: [
    (Story) => (
      <TooltipProvider>
        <div className="flex justify-center p-16">
          <Story />
        </div>
      </TooltipProvider>
    ),
  ],
  parameters: {
    docs: {
      description: {
        component:
          "Expanded departs from Serendie: inverse colours come from on-surface and surface, " +
          "and the tooltip opens on keyboard focus as well as hover.",
      },
    },
  },
} satisfies Meta<typeof Tooltip>;

export default meta;

type Story = StoryObj<typeof meta>;

export const OnFocus: Story = {
  play: async ({ canvasElement }) => {
    const trigger = within(canvasElement).getByRole("button", { name: "Delete rule" });
    await userEvent.tab();
    await expect(trigger).toHaveFocus();
    await expect(getComputedStyle(trigger).outlineWidth).not.toBe("0px");
    const tooltip = await within(document.body).findByRole("tooltip");
    await expect(tooltip).toHaveTextContent("Delete rule");
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(within(document.body).queryByRole("tooltip")).toBeNull());
    await expect(trigger).toHaveFocus();
  },
};

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  play: async ({ canvasElement }) => expectNoHorizontalPageScroll(canvasElement),
};
