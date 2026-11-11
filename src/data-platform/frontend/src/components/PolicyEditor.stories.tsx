import type { Meta, StoryObj } from "@storybook/react-vite";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, fn, screen, userEvent, waitFor, within } from "storybook/test";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { PHONE } from "@/stories/phone";
import { POLICIES } from "@/stories/storyData";
import { FALLBACK_POLICY_CONTENT } from "@/lib/policyDraft";
import { PolicyEditor } from "./PolicyEditor";

const meta = {
  title: "Components/Policy editor",
  component: PolicyEditor,
  args: { policy: POLICIES[1]!, onClose: fn() },
  decorators: [
    (Story) => (
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <Story />
      </QueryClientProvider>
    ),
  ],
  beforeEach({ msw }) {
    msw.use(...lakehouseHandlers());
  },
} satisfies Meta<typeof PolicyEditor>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Edit: Story = {
  play: async ({ args }) => {
    const dialog = await screen.findByRole("dialog", { name: "Edit policy" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(args.onClose).toHaveBeenCalled());
  },
};

export const New: Story = {
  args: { policy: undefined, template: { ...FALLBACK_POLICY_CONTENT, description: "" } },
  play: async () => {
    const dialog = await screen.findByRole("dialog", { name: "New policy" });
    await expect(within(dialog).getByRole("textbox", { name: "Name" })).toHaveValue("");
  },
};

export const Invalid: Story = {
  play: async ({ args }) => {
    const dialog = await screen.findByRole("dialog", { name: "Edit policy" });
    await userEvent.clear(within(dialog).getByRole("spinbutton", { name: "Reconcile interval (seconds)" }));
    await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await expect(within(dialog).getByRole("alert")).toHaveTextContent("Reconcile interval must be a whole number.");
    await expect(args.onClose).not.toHaveBeenCalled();
  },
};

export const Escape: Story = {
  play: async ({ args }) => {
    await screen.findByRole("dialog", { name: "Edit policy" });
    await userEvent.keyboard("{Escape}");
    await expect(args.onClose).toHaveBeenCalled();
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await screen.findByRole("dialog", { name: "Edit policy" });
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
