import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";
import { expectFocusRing } from "../../stories/assertions";
import { SerendieSymbolBookOpen, SerendieSymbolLayoutGrid } from "../../icons";
import { SideNavigation } from "./SideNavigation";

const items = [
  { href: "/tables", label: "Tables", icon: SerendieSymbolLayoutGrid, isActive: false },
  { href: "/runs", label: "Runs", icon: SerendieSymbolBookOpen, isActive: true },
  { href: "/presets", label: "Presets", icon: SerendieSymbolLayoutGrid, isActive: false },
];

const meta = {
  title: "Components/SideNavigation",
  component: SideNavigation,
  args: {
    items,
    onNavigate: fn(),
    renderLink: (item, children) => (
      <a
        href={`#${item.href}`}
        onClick={(event) => event.preventDefault()}
      >
        {children}
      </a>
    ),
  },
  parameters: {
    docs: {
      description: {
        component:
          "Not in Serendie. Items are 36px high expanded and 44px below 768px and under a " +
          "coarse pointer.",
      },
    },
  },
} satisfies Meta<typeof SideNavigation>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: (args) => (
    <div className="w-56">
      <SideNavigation {...args} />
    </div>
  ),
  play: async ({ canvasElement, args }) => {
    const nav = within(canvasElement).getByRole("navigation", { name: "Main" });
    const links = within(nav).getAllByRole("link") as [HTMLElement, HTMLElement, HTMLElement];
    await expect(links).toHaveLength(3);
    await expect(links[1]).toHaveAttribute("aria-current", "page");
    await expect(links[0]).not.toHaveAttribute("aria-current");
    await userEvent.tab();
    await expectFocusRing(links[0]);
    await userEvent.tab();
    await expectFocusRing(links[1]);
    await userEvent.tab();
    await expectFocusRing(links[2]);
    await userEvent.keyboard("{Enter}");
    await expect(args.onNavigate).toHaveBeenCalledTimes(1);
  },
};

export const Phone: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  render: Default.render,
  play: async ({ canvasElement }) => {
    const link = within(canvasElement).getAllByRole("link")[0] as HTMLElement;
    await expect(link.getBoundingClientRect().height).toBeGreaterThanOrEqual(44);
  },
};
