import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, waitFor, within } from "storybook/test";
import { applyTheme } from "../../theme/applyTheme";
import { expectNoHorizontalPageScroll } from "../../stories/assertions";
import { CategoryBadge } from "./CategoryBadge";

const meta = {
  title: "Components/CategoryBadge",
  component: CategoryBadge,
  args: { category: "neutral", children: "Unmanaged" },
  parameters: {
    docs: {
      description: {
        component:
          "No Serendie counterpart. Says which group a thing belongs to, never how it is doing, so " +
          "it keeps off the status colours (StatusBadge). accent is the theme's light tint and has no " +
          "border, hover or pointer cursor, so it does not read as a button; neutral is grey; muted " +
          "is a fainter grey with strikethrough and italics for something that is gone. The text " +
          "always stays: colour never carries the meaning alone.",
      },
    },
  },
} satisfies Meta<typeof CategoryBadge>;

export default meta;

type Story = StoryObj<typeof meta>;

function AllCategories() {
  return (
    <div className="flex flex-wrap gap-2 p-4">
      <CategoryBadge category="accent">Managed</CategoryBadge>
      <CategoryBadge category="neutral">Unmanaged</CategoryBadge>
      <CategoryBadge category="muted">Dropped</CategoryBadge>
    </div>
  );
}

async function expectThreeDistinctAndInert(canvasElement: HTMLElement) {
  const canvas = within(canvasElement);
  const accent = canvas.getByText("Managed");
  const neutral = canvas.getByText("Unmanaged");
  const muted = canvas.getByText("Dropped");
  const backgrounds = [accent, neutral, muted].map((badge) => getComputedStyle(badge).backgroundColor);
  await expect(new Set(backgrounds).size).toBe(3);
  await expect(getComputedStyle(muted).textDecorationLine).toBe("line-through");
  await expect(getComputedStyle(muted).fontStyle).toBe("italic");
  for (const badge of [accent, neutral]) {
    await expect(getComputedStyle(badge).textDecorationLine).toBe("none");
  }
  for (const badge of [accent, neutral, muted]) {
    await expect(getComputedStyle(badge).cursor).not.toBe("pointer");
    await expect(badge).not.toHaveAttribute("tabindex");
  }
  await expect(canvas.queryAllByRole("button")).toHaveLength(0);
  await expect(canvas.queryAllByRole("link")).toHaveLength(0);
  await userEvent.tab();
  await expect(canvasElement.ownerDocument.activeElement).toBe(canvasElement.ownerDocument.body);
  return backgrounds;
}

export const Accent: Story = {
  args: { category: "accent", children: "Managed" },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText("Managed")).toBeVisible();
  },
};

export const Neutral: Story = {
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText("Unmanaged")).toBeVisible();
  },
};

export const Muted: Story = {
  args: { category: "muted", children: "Dropped" },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByText("Dropped")).toBeVisible();
  },
};

export const Konjo: Story = {
  globals: { theme: "konjo" },
  render: () => <AllCategories />,
  play: async ({ canvasElement }) => {
    await expectThreeDistinctAndInert(canvasElement);
  },
};

export const Asagi: Story = {
  globals: { theme: "asagi" },
  render: () => <AllCategories />,
  play: async ({ canvasElement }) => {
    await expectThreeDistinctAndInert(canvasElement);
  },
};

export const Kurikawa: Story = {
  globals: { theme: "kurikawa" },
  render: () => <AllCategories />,
  play: async ({ canvasElement }) => {
    await expectThreeDistinctAndInert(canvasElement);
  },
};

export const FollowsThemeSwitch: Story = {
  render: () => <AllCategories />,
  play: async ({ canvasElement }) => {
    const root = document.documentElement;
    const accent = within(canvasElement).getByText("Managed");
    applyTheme(root, "konjo");
    await waitFor(() => expect(getComputedStyle(accent).backgroundColor).not.toBe("rgba(0, 0, 0, 0)"));
    const konjo = getComputedStyle(accent).backgroundColor;
    applyTheme(root, "kurikawa");
    await waitFor(() => expect(getComputedStyle(accent).backgroundColor).not.toBe(konjo));
    applyTheme(root, "konjo");
  },
};

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  render: () => <AllCategories />,
  play: async ({ canvasElement }) => {
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
