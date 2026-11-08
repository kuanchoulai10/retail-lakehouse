import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";
import { expectNoHorizontalPageScroll } from "../../stories/assertions";
import { Button } from "./Button";

const meta = {
  title: "Components/Button",
  component: Button,
  args: { children: "Run compaction", onClick: fn() },
  parameters: {
    docs: {
      description: {
        component:
          "Expanded departs from Serendie: medium is 36px high (Serendie 48px) and small is " +
          "32px; both stay 44px below 768px and under a coarse pointer.",
      },
    },
  },
} satisfies Meta<typeof Button>;

export default meta;

type Story = StoryObj<typeof meta>;

async function expectFocusRing(element: HTMLElement) {
  await expect(element).toHaveFocus();
  await expect(getComputedStyle(element).outlineWidth).not.toBe("0px");
}

export const Filled: Story = {
  args: { styleType: "filled" },
  play: async ({ canvasElement, args }) => {
    const button = within(canvasElement).getByRole("button", { name: "Run compaction" });
    await userEvent.tab();
    await expectFocusRing(button);
    await userEvent.keyboard("{Enter}");
    await expect(args.onClick).toHaveBeenCalledTimes(1);
    await userEvent.keyboard(" ");
    await expect(args.onClick).toHaveBeenCalledTimes(2);
  },
};

export const Outlined: Story = {
  args: { styleType: "outlined" },
  play: async ({ canvasElement }) => {
    const button = within(canvasElement).getByRole("button", { name: "Run compaction" });
    await expect(getComputedStyle(button).borderTopWidth).toBe("2px");
  },
};

export const Negative: Story = {
  args: { styleType: "negative", children: "Delete table" },
  play: async ({ canvasElement }) => {
    const button = within(canvasElement).getByRole("button", { name: "Delete table" });
    const probe = (name: string) => {
      const el = document.createElement("div");
      el.style.backgroundColor = getComputedStyle(document.documentElement).getPropertyValue(name);
      document.body.appendChild(el);
      const resolved = getComputedStyle(el).backgroundColor;
      el.remove();
      return resolved;
    };
    await expect(getComputedStyle(button).backgroundColor).toBe(probe("--ds-negative"));
    await expect(getComputedStyle(button).color).toBe(probe("--ds-on-negative"));
    await userEvent.tab();
    await expectFocusRing(button);

    await expect(button.className).toContain("enabled:hover:after:bg-hovered");
  },
};

export const Ghost: Story = { args: { styleType: "ghost" } };

export const Small: Story = { args: { size: "small" } };

export const Disabled: Story = {
  args: { disabled: true },
  play: async ({ canvasElement, args }) => {
    const button = within(canvasElement).getByRole("button", { name: "Run compaction" });
    await userEvent.click(button);
    await userEvent.tab();
    await expect(button).not.toHaveFocus();
    await expect(args.onClick).not.toHaveBeenCalled();
  },
};

export const Loading: Story = {
  args: { isLoading: true },
  play: async ({ canvasElement, args }) => {
    const button = within(canvasElement).getByRole("button", { name: "Run compaction" });
    await expect(button).toHaveAttribute("aria-busy", "true");
    await userEvent.click(button);
    await expect(args.onClick).not.toHaveBeenCalled();
  },
};

export const AsChild: Story = {
  render: (args) => (
    <Button {...args} asChild>
      <a href="#maintenance">Open maintenance</a>
    </Button>
  ),
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("link", { name: "Open maintenance" })).toBeVisible();
  },
};

export const InsideForm: Story = {
  render: (args) => (
    <form onSubmit={(event) => event.preventDefault()}>
      <Button {...args}>Run compaction</Button>
    </form>
  ),
  play: async ({ canvasElement }) => {
    const form = canvasElement.querySelector("form") as HTMLFormElement;
    const onSubmit = fn();
    form.addEventListener("submit", onSubmit);
    const button = within(canvasElement).getByRole("button", { name: "Run compaction" });
    await expect(button).toHaveAttribute("type", "button");
    await userEvent.click(button);
    await expect(onSubmit).not.toHaveBeenCalled();
  },
};

export const Touch: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  render: (args) => (
    <div className="flex flex-col items-start gap-2 p-4">
      <Button {...args}>Medium</Button>
      <Button {...args} size="small">
        Small
      </Button>
    </div>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    for (const name of ["Medium", "Small"]) {
      await expect(canvas.getByRole("button", { name }).getBoundingClientRect().height).toBe(44);
    }
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const Desktop: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  render: (args) => (
    <div className="flex items-start gap-2 p-4">
      <Button {...args}>Medium</Button>
      <Button {...args} size="small">
        Small
      </Button>
    </div>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("button", { name: "Medium" }).getBoundingClientRect().height).toBe(36);
    await expect(canvas.getByRole("button", { name: "Small" }).getBoundingClientRect().height).toBe(32);
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
