import { ThemeProvider, TooltipProvider } from "@retail-lakehouse/design-system";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { MemoryRouter } from "react-router";
import { expect, userEvent, within } from "storybook/test";
import { getGetTableDiscoveryRulesMockHandler } from "@/api/generated/discovery-rules/discovery-rules.msw";
import { apiError } from "@/stories/apiError";
import { AppShell } from "@/components/AppShell";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { lakehouseHandlers } from "@/stories/lakehouseHandlers";
import { PHONE } from "@/stories/phone";
import { DiscoveryRulesPage } from "./DiscoveryRulesPage";

// /discovery-rules now redirects to the discovery policies, so until this page is deleted its
// stories mount it directly, inside the console shell as ConsolePage would.
function OldRulesPage() {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { retry: false, staleTime: Infinity, refetchOnWindowFocus: false } },
      }),
  );
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <MemoryRouter>
            <AppShell>
              <DiscoveryRulesPage />
            </AppShell>
          </MemoryRouter>
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

const meta = {
  title: "Pages/Discovery rules",
  component: OldRulesPage,
  beforeEach({ msw }) {
    msw.use(...lakehouseHandlers());
  },
} satisfies Meta<typeof OldRulesPage>;

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
