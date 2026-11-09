import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { IconMenu2 } from "../../icons";
import { expectNoHorizontalPageScroll } from "../../stories/assertions";
import { Button } from "../Button/Button";
import { IconButton } from "../IconButton/IconButton";
import { TopAppBar } from "./TopAppBar";

const meta = {
  title: "Components/TopAppBar",
  component: TopAppBar,
  args: { title: "Lakehouse Console" },
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "Expanded departs from Serendie: the bar is 56px high with expanded typography.",
      },
    },
  },
} satisfies Meta<typeof TopAppBar>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("banner")).toBeInTheDocument();
    await expect(within(canvasElement).getByText("Lakehouse Console")).toBeVisible();
  },
};

export const WithItems: Story = {
  args: {
    headingIconButton: <IconButton aria-label="Menu" styleType="ghost" icon={<IconMenu2 />} />,
    trailingItems: <Button styleType="outlined">Sign out</Button>,
  },
};

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  args: { ...WithItems.args, title: "A rather long product name for a narrow screen" },
  play: async ({ canvasElement }) => {
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
