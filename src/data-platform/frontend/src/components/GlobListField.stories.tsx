import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { expect, userEvent, within } from "storybook/test";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { PHONE } from "@/stories/phone";
import { GlobListField } from "./GlobListField";

function Field({ initial }: { initial: string[] }) {
  const [globs, setGlobs] = useState(initial);
  return (
    <div className="max-w-md bg-surface p-4">
      <GlobListField
        label="Tables"
        hint="Globs on the table name; any one may match."
        globs={globs}
        onChange={setGlobs}
      />
    </div>
  );
}

const meta = {
  title: "Components/Glob list field",
  component: Field,
  args: { initial: ["tmp_*", "staging_*"] },
} satisfies Meta<typeof Field>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const input = canvas.getByRole("textbox", { name: "New tables glob" });
    await userEvent.type(input, "orders_*{Enter}");
    await expect(canvas.getByText("orders_*")).toBeVisible();
    await expect(input).toHaveFocus();
    await userEvent.click(canvas.getByRole("button", { name: "Remove tables glob tmp_*" }));
    await expect(canvas.queryByText("tmp_*")).not.toBeInTheDocument();
  },
};

export const Empty: Story = { args: { initial: [] } };

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
