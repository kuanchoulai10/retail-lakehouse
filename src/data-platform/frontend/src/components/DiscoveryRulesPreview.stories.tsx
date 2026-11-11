import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { ApiError } from "@/api/apiError";
import type { DiscoveryRuleDraft } from "@/lib/discoveryRuleDraft";
import { expectNoHorizontalPageScroll } from "@/stories/expectNoHorizontalPageScroll";
import { PHONE } from "@/stories/phone";
import { DiscoveryRulesPreview } from "./DiscoveryRulesPreview";

const RULES: DiscoveryRuleDraft[] = [
  { key: "rule-tmp", id: "rule-tmp", priority: 10, action: "exclude", enabled: true, catalogs: ["*"], namespaces: ["*"], tables: ["tmp_*"] },
  { key: "new-1", id: null, priority: 20, action: "include", enabled: true, catalogs: ["iceberg"], namespaces: ["retail"], tables: ["*"] },
];

const meta = {
  title: "Components/Discovery rules preview",
  component: DiscoveryRulesPreview,
  decorators: [(Story) => <div className="max-w-md bg-surface p-4"><Story /></div>],
  args: {
    rules: RULES,
    isFetching: false,
    error: null,
    preview: {
      tables: [
        { catalog: "iceberg", namespace: "retail", table: "orders", rule_id: "#1", managed: true },
        { catalog: "iceberg", namespace: "retail", table: "customers", rule_id: "#1", managed: true },
        { catalog: "iceberg", namespace: "retail", table: "tmp_backfill", rule_id: "rule-tmp", managed: false },
        { catalog: "analytics", namespace: "marts.finance", table: "revenue_by_day_and_region", rule_id: null, managed: false },
      ],
      managed: 2,
      unmanaged: 2,
    },
  },
} satisfies Meta<typeof DiscoveryRulesPreview>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText("2 managed, 2 unmanaged")).toBeVisible();
    await expect(canvas.getByRole("group", { name: "Priority 20, include (unsaved): 2 tables, managed" })).toBeVisible();
  },
};

export const Loading: Story = { args: { preview: undefined, isFetching: true } };

export const NoTables: Story = { args: { preview: { tables: [], managed: 0, unmanaged: 0 } } };

export const Failed: Story = { args: { preview: undefined, error: new ApiError(422, "Invalid glob '[' in tables") } };

export const Phone: Story = {
  globals: PHONE,
  play: async ({ canvasElement }) => {
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
