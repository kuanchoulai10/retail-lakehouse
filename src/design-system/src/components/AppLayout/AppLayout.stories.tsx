import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { expect, userEvent, waitFor, within } from "storybook/test";
import { SerendieSymbolBookOpen, SerendieSymbolLayoutGrid } from "../../icons";
import {
  expectFocusRing,
  expectNoHorizontalPageScroll,
  portalQueries,
} from "../../stories/assertions";
import type { SideNavigationProps } from "../SideNavigation/SideNavigation";
import { AppLayout } from "./AppLayout";

const meta = {
  title: "Components/AppLayout",
  component: AppLayout,
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "Not in Serendie. From 768px a persistent 224px sidebar sits under the top bar; " +
          "below it a menu button opens the navigation in a left drawer. " +
          "`renderProductLink` turns the product name into a link (Slot carries the focus ring onto it).",
      },
    },
  },
} satisfies Meta<typeof AppLayout>;

export default meta;

type Story = StoryObj<typeof meta>;

function Harness() {
  const [path, setPath] = useState("/tables");
  const navigation: SideNavigationProps = {
    items: [
      { href: "/tables", label: "Tables", icon: SerendieSymbolLayoutGrid, isActive: path === "/tables" },
      { href: "/runs", label: "Runs", icon: SerendieSymbolBookOpen, isActive: path === "/runs" },
    ],
    renderLink: (item, children) => (
      <a
        href={`#${item.href}`}
        onClick={(event) => {
          event.preventDefault();
          setPath(item.href);
        }}
      >
        {children}
      </a>
    ),
  };
  return (
    <AppLayout
      productName="Lakehouse Console"
      navigation={navigation}
      renderProductLink={(children) => (
        <a
          href="#/tables"
          onClick={(event) => {
            event.preventDefault();
            setPath("/tables");
          }}
        >
          {children}
        </a>
      )}
    >
      <h1 className="type-headline-small">Page {path}</h1>
    </AppLayout>
  );
}

export const Desktop: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  args: {} as never,
  render: () => <Harness />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("banner")).toBeVisible();
    const nav = canvas.getByRole("navigation", { name: "Main" });
    await expect(nav.closest("aside")?.getBoundingClientRect().width).toBe(224);
    await expect(canvasElement.querySelector("[aria-label='Open navigation menu']")).not.toBeVisible();
    await expect(canvas.getByRole("main")).toBeVisible();
  },
};

export const ProductLink: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  args: {} as never,
  render: () => <Harness />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("link", { name: "Runs" }));
    await expect(canvas.getByRole("heading", { name: "Page /runs" })).toBeVisible();
    const product = within(canvas.getByRole("banner")).getByRole("link", { name: "Lakehouse Console" });
    await expect(product).toHaveAttribute("href", "#/tables");
    (document.activeElement as HTMLElement | null)?.blur();
    await userEvent.tab();
    await expectFocusRing(product);
    await userEvent.keyboard("{Enter}");
    await expect(canvas.getByRole("heading", { name: "Page /tables" })).toBeVisible();
  },
};

export const PhoneDrawer: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  args: {} as never,
  render: () => <Harness />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const portal = portalQueries(canvasElement);
    const menu = canvas.getByRole("button", { name: "Open navigation menu" });
    await expect(canvas.queryByRole("navigation", { name: "Main" })).toBeNull();
    await userEvent.tab();
    await expectFocusRing(menu);
    await userEvent.keyboard("{Enter}");
    const dialog = await portal.findByRole("dialog");
    await expect(within(dialog).getByRole("navigation", { name: "Main" })).toBeVisible();
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(portal.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(menu).toHaveFocus());

    await userEvent.click(menu);
    const reopened = await portal.findByRole("dialog");
    await userEvent.click(within(reopened).getByRole("link", { name: "Runs" }));
    await waitFor(() => expect(portal.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(canvas.getByRole("main")).toHaveFocus());
    await expect(canvas.getByRole("heading", { name: "Page /runs" })).toBeVisible();
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
