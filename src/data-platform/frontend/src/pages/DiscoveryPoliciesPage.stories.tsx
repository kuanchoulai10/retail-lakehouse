import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, screen, userEvent, within } from "storybook/test";
import {
  getListScannedCatalogsMockHandler,
  getListTableDiscoveryPoliciesMockHandler,
} from "@/api/generated/discovery-policies/discovery-policies.msw";
import { apiError } from "@/stories/apiError";
import { ConsolePage } from "@/stories/ConsolePage";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";
import { DISCOVERY_POLICIES } from "@/stories/storyData";

const meta = {
  title: "Pages/Discovery policies",
  component: ConsolePage,
  args: { route: "/discovery-policies" },
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
  // Not `throw new Error`: the story named Error below shadows it in this module.
  if (found === undefined) throw new globalThis.Error(`no policy ${name}`);
  return found;
}

export const Loaded: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("Sales tables, without the temporary ones")).toBeVisible();
    const sales = row(canvasElement, "sales-tables");
    await expect(within(sales).getByRole("link", { name: "sales-tables" })).toBeVisible();
    await expect(within(sales).getByRole("button", { name: "Delete sales-tables" })).toBeDisabled();
    const defaultRow = row(canvasElement, "default");
    await expect(within(defaultRow).getByText("Default")).toBeVisible();
    await expect(within(defaultRow).getByRole("button", { name: "Delete default" })).toBeDisabled();
    await expect(canvas.getByRole("link", { name: "Discovery policies" })).toHaveAttribute("aria-current", "page");
    await expect(canvas.queryByRole("alert")).toBeNull();
  },
};

export const OnlyDefault: Story = {
  beforeEach({ msw }) {
    msw.use(getListTableDiscoveryPoliciesMockHandler({ policies: [DISCOVERY_POLICIES[0]!] }));
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("link", { name: "default" })).toBeVisible();
    await expect(canvas.queryByRole("link", { name: "sales-tables" })).toBeNull();
    await expect(canvas.getByRole("button", { name: "New policy" })).toBeEnabled();
  },
};

export const NewPolicy: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole("button", { name: "New policy" }));
    const dialog = await screen.findByRole("dialog", { name: "New discovery policy" });
    await expect(within(dialog).getByRole("combobox", { name: "When no rule matches" })).toHaveTextContent(
      "Do not manage",
    );
  },
};

export const Error: Story = {
  beforeEach({ msw }) {
    msw.use(apiError("get", "/v1/discovery-policies", "database unavailable"));
  },
  play: async ({ canvasElement }) => {
    await expect(
      await within(canvasElement).findByText("Could not load discovery policies: database unavailable"),
    ).toBeVisible();
  },
};

export const CannotAccess: Story = {
  beforeEach({ msw }) {
    msw.use(
      getListScannedCatalogsMockHandler({
        catalogs: [
          {
            catalog: "finance",
            last_discovered_at: "2026-11-08T08:10:00Z",
            failure: {
              reason: "cannot_access",
              detail: "the platform's catalog credential cannot read catalog finance",
              failed_at: "2026-11-09T08:10:00Z",
            },
          },
          { catalog: "iceberg", last_discovered_at: "2026-11-09T08:10:00Z", failure: null },
        ],
      }),
    );
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const alert = await canvas.findByRole("alert");
    await expect(alert).toHaveTextContent("Cannot access: finance");
    await expect(within(alert).getByText("the platform's catalog credential cannot read catalog finance")).toBeVisible();
    await expect(await canvas.findByText("Sales tables, without the temporary ones")).toBeVisible();
  },
};

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await within(canvasElement).findByText("Sales tables, without the temporary ones");
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const OldRulesUrl: Story = {
  args: { route: "/discovery-rules" },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("heading", { name: "Discovery policies", level: 1 })).toBeVisible();
    await expect(await canvas.findByRole("link", { name: "sales-tables" })).toBeVisible();
  },
};
