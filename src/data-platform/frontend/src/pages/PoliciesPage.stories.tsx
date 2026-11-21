import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, screen, userEvent, waitFor, within } from "storybook/test";
import { getListTableMaintenancePoliciesMockHandler } from "@/api/generated/maintenance-policies/maintenance-policies.msw";
import { apiError } from "@/stories/apiError";
import { apiPending } from "@/stories/apiPending";
import { ConsolePage } from "@/stories/ConsolePage";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";
import { POLICIES } from "@/stories/storyData";

const meta = {
  title: "Pages/Policies",
  component: ConsolePage,
  args: { route: "/policies" },
  beforeEach({ msw }) {
    msw.use(...lakehouseHandlers());
  },
} satisfies Meta<typeof ConsolePage>;

export default meta;
type Story = StoryObj<typeof meta>;

function row(canvasElement: HTMLElement, name: string): HTMLElement {
  const found = within(canvasElement)
    .getAllByRole("row")
    .find((r) => within(r).queryAllByRole("cell")[0]?.textContent?.startsWith(name));
  if (found === undefined) throw new Error(`no policy ${name}`);
  return found;
}

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("Compacts whole tables once a day")).toBeVisible();
    const nightly = row(canvasElement, "retail-nightly");
    await expect(await within(nightly).findByRole("link", { name: "iceberg.retail" })).toBeVisible();
    await expect(within(nightly).getByText("No longer in the catalog")).toBeVisible();
    await expect(within(row(canvasElement, "default")).getByText("Default")).toBeVisible();
    await expect(within(row(canvasElement, "default")).getByRole("button", { name: "Delete default" })).toBeDisabled();
    await expect(canvas.getByRole("columnheader", { name: "Checks" })).toBeVisible();
    await expect(within(row(canvasElement, "default")).getByText("Every 1 h, and 5 min after a commit")).toBeVisible();
    await expect(within(nightly).getByText("Every 1 d")).toBeVisible();
  },
};

export const OnlyDefault: Story = {
  beforeEach({ msw }) {
    msw.use(getListTableMaintenancePoliciesMockHandler({ policies: [POLICIES[0]!] }));
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("Platform default")).toBeVisible();
    await expect(canvas.getByText("Not attached")).toBeVisible();
  },
};

export const NoDefault: Story = {
  beforeEach({ msw }) {
    msw.use(getListTableMaintenancePoliciesMockHandler({ policies: POLICIES.slice(1) }));
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(
      await canvas.findByText(
        "The default policy is missing, so a new policy has nothing to start from. Reload the page.",
      ),
    ).toBeVisible();
    await expect(canvas.getByRole("button", { name: "New policy" })).toBeDisabled();
  },
};

export const AttachmentsLoading: Story = {
  beforeEach({ msw }) {
    msw.use(apiPending("/v1/maintenance-policies/retail-nightly/attachments"));
  },
  play: async ({ canvasElement }) => {
    await within(canvasElement).findByText("Compacts whole tables once a day");
    await expect(within(canvasElement).getByText("Loading where retail-nightly is attached")).toBeInTheDocument();
  },
};

export const Editor: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await canvas.findByText("Compacts whole tables once a day");
    await userEvent.click(canvas.getByRole("button", { name: "Edit retail-nightly" }));
    const dialog = await screen.findByRole("dialog", { name: "Edit policy" });
    const rewrite = within(dialog).getByRole("group", { name: "Rewrite data files" });
    await expect(within(rewrite).getByRole("combobox", { name: "Per" })).toHaveTextContent("Whole table");
    await expect(within(rewrite).getByRole("textbox", { name: "Reducible files at most" })).toHaveValue("20");
    await expect(within(dialog).getByRole("switch", { name: "Check after catalog commits" })).not.toBeChecked();
    await expect(within(dialog).queryByRole("combobox", { name: "Priority" })).toBeNull();
  },
};

export const NewPolicy: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole("button", { name: "New policy" }));
    const dialog = await screen.findByRole("dialog", { name: "New policy" });
    await expect(within(dialog).getByRole("textbox", { name: "Name" })).toHaveValue("");
    await expect(within(dialog).getByRole("textbox", { name: "Description" })).toHaveValue("");
  },
};

export const Conflict: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("put", "/v1/maintenance-policies/retail-nightly", "stale version", 409));
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await canvas.findByText("Compacts whole tables once a day");
    await userEvent.click(canvas.getByRole("button", { name: "Edit retail-nightly" }));
    const dialog = await screen.findByRole("dialog", { name: "Edit policy" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await expect(
      await within(dialog).findByText("Someone else changed this policy. Reload to see their version."),
    ).toBeVisible();
    await expect(within(dialog).getByRole("button", { name: "Reload" })).toBeVisible();
  },
};

export const LoadError: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("get", "/v1/maintenance-policies", "database unavailable"));
  },
  play: async ({ canvasElement }) => {
    await expect(
      await within(canvasElement).findByText("Could not load policies: database unavailable"),
    ).toBeVisible();
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await canvas.findByText("Compacts whole tables once a day");
    await waitFor(() => expect(canvas.getAllByRole("link", { name: "iceberg.retail" }).length).toBeGreaterThan(0));
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const PhoneEditor: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await canvas.findByText("Compacts whole tables once a day");
    await userEvent.click(canvas.getByRole("button", { name: "Edit retail-nightly" }));
    await screen.findByRole("dialog", { name: "Edit policy" });
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
