import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import { getGetTableDiscoveryRulesMockHandler } from "@/api/generated/discovery-rules/discovery-rules.msw";
import { apiError } from "@/stories/apiError";
import { ConsolePage } from "@/stories/ConsolePage";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";

const meta = {
  title: "Pages/Discovery rules",
  component: ConsolePage,
  args: { route: "/discovery-rules" },
  beforeEach({ msw }) {
    msw.use(...lakehouseHandlers());
  },
} satisfies Meta<typeof ConsolePage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("retail")).toBeVisible();
  },
};

export const NoRules: Story = {
  beforeEach({ msw }) {
    msw.use(getGetTableDiscoveryRulesMockHandler({ version: 0, rules: [] }));
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("No discovery rules. No table is managed.")).toBeVisible();
  },
};

export const Conflict: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("put", "/v1/discovery-rules", "stale version", 409));
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole("switch", { name: "Rule 50 enabled" }));
    await userEvent.click(canvas.getByRole("button", { name: "Save" }));
    await expect(
      await canvas.findByText("Someone else changed these rules. Reload to see their version."),
    ).toBeVisible();
    await expect(canvas.getByRole("switch", { name: "Rule 50 enabled" })).toBeChecked();
  },
};

export const Saved: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole("switch", { name: "Rule 50 enabled" }));
    await userEvent.click(canvas.getByRole("button", { name: "Save" }));
    await expect(await canvas.findByText("Saved. Discovering tables…")).toBeVisible();
  },
};

export const LoadError: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("get", "/v1/discovery-rules", "database unavailable"));
  },
  play: async ({ canvasElement }) => {
    await expect(
      await within(canvasElement).findByText("Could not load discovery rules: database unavailable"),
    ).toBeVisible();
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await within(canvasElement).findByText("retail");
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
