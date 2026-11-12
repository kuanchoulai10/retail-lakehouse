import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState, type ReactNode } from "react";
import { expect, userEvent, waitFor, within } from "storybook/test";
import { IconBook, IconPalette, IconTable } from "../../icons";
import { IconButton } from "../IconButton/IconButton";
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
          "Not in Serendie. From 768px a persistent 224px sidebar sits under the top bar; the " +
          "button at the start of the top bar collapses it to a 56px rail of icons, each named " +
          "by a tooltip, and the choice is remembered in this browser. Below 768px that button " +
          "opens the navigation in a left drawer instead. `leadingItems` sit just after the " +
          "product name, `trailingItems` at the far end. " +
          "`renderProductLink` turns the product name into a link (Slot carries the focus ring onto it).",
      },
    },
  },
} satisfies Meta<typeof AppLayout>;

export default meta;

type Story = StoryObj<typeof meta>;

function Harness({ leadingItems }: { leadingItems?: ReactNode }) {
  const [path, setPath] = useState("/tables");
  const navigation: SideNavigationProps = {
    items: [
      { href: "/tables", label: "Tables", icon: IconTable, isActive: path === "/tables" },
      { href: "/runs", label: "Runs", icon: IconBook, isActive: path === "/runs" },
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
      leadingItems={leadingItems}
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
    await expect(within(canvas.getByRole("link", { name: "Tables" })).getByText("Tables")).toBeVisible();
    await expect(canvas.getByRole("main")).toBeVisible();
  },
};

const SIDEBAR_STORAGE_KEY = "ds-app-layout-sidebar-collapsed";

function forgetSidebarChoice() {
  window.localStorage.removeItem(SIDEBAR_STORAGE_KEY);
  return () => window.localStorage.removeItem(SIDEBAR_STORAGE_KEY);
}

export const CollapsedSidebar: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  args: {} as never,
  beforeEach: forgetSidebarChoice,
  render: () => <Harness />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const portal = portalQueries(canvasElement);
    const aside = canvas.getByRole("navigation", { name: "Main" }).closest("aside") as HTMLElement;
    const collapse = canvas.getByRole("button", { name: "Collapse navigation" });
    await expect(collapse).toHaveAttribute("aria-expanded", "true");
    await expect(collapse).toHaveAttribute("aria-controls", aside.id);
    (document.activeElement as HTMLElement | null)?.blur();
    await userEvent.tab();
    await expectFocusRing(collapse);
    await userEvent.keyboard("{Enter}");
    await waitFor(() => expect(aside.getBoundingClientRect().width).toBe(56));
    const expand = canvas.getByRole("button", { name: "Expand navigation" });
    await expect(expand).toHaveAttribute("aria-expanded", "false");
    await expect(expand).toHaveFocus();
    await expect(window.localStorage.getItem(SIDEBAR_STORAGE_KEY)).toBe("true");

    const runs = canvas.getByRole("link", { name: "Runs" });
    await expect(within(runs).getByText("Runs").getBoundingClientRect().width).toBeLessThanOrEqual(1);
    await userEvent.tab();
    await userEvent.tab();
    await userEvent.tab();
    await expectFocusRing(runs);
    await expect(await portal.findByRole("tooltip")).toHaveTextContent("Runs");
    await userEvent.keyboard("{Enter}");
    await expect(canvas.getByRole("heading", { name: "Page /runs" })).toBeVisible();

    await userEvent.click(expand);
    await waitFor(() => expect(aside.getBoundingClientRect().width).toBe(224));
    const expandedRuns = canvas.getByRole("link", { name: "Runs" });
    await expect(within(expandedRuns).getByText("Runs").getBoundingClientRect().width).toBeGreaterThan(1);
    await expect(window.localStorage.getItem(SIDEBAR_STORAGE_KEY)).toBe("false");
  },
};

export const RemembersCollapsedSidebar: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  args: {} as never,
  beforeEach: () => {
    window.localStorage.setItem(SIDEBAR_STORAGE_KEY, "true");
    return () => window.localStorage.removeItem(SIDEBAR_STORAGE_KEY);
  },
  render: () => <Harness />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const aside = canvas.getByRole("navigation", { name: "Main" }).closest("aside") as HTMLElement;
    await expect(aside.getBoundingClientRect().width).toBe(56);
    await expect(canvas.getByRole("button", { name: "Expand navigation" })).toBeVisible();
  },
};

export const LeadingItems: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  args: {} as never,
  render: () => (
    <Harness
      leadingItems={<IconButton aria-label="Colour theme" styleType="ghost" icon={<IconPalette />} />}
    />
  ),
  play: async ({ canvasElement }) => {
    const banner = within(canvasElement).getByRole("banner");
    const product = within(banner).getByRole("link", { name: "Lakehouse Console" });
    const leading = within(banner).getByRole("button", { name: "Colour theme" });
    const productBox = product.getBoundingClientRect();
    const leadingBox = leading.getBoundingClientRect();
    await expect(leadingBox.left).toBeGreaterThanOrEqual(productBox.right);
    await expect(leadingBox.left - productBox.right).toBeLessThan(32);
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
    await expect(canvas.getByRole("button", { name: "Collapse navigation" })).toHaveFocus();
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
    await expect(canvasElement.querySelector("[aria-label='Collapse navigation']")).not.toBeVisible();
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

const EXPANDED_QUERY = "(min-width: 48rem)";
const expandedWindow = { matches: false, listeners: new Set<(event: MediaQueryListEvent) => void>() };

// Stands in for the viewport crossing 768px: only the expanded-window query is faked.
function fakeExpandedQuery() {
  const realMatchMedia = window.matchMedia.bind(window);
  expandedWindow.matches = false;
  expandedWindow.listeners.clear();
  window.matchMedia = (query: string) => {
    if (query !== EXPANDED_QUERY) return realMatchMedia(query);
    return {
      get matches() {
        return expandedWindow.matches;
      },
      media: query,
      onchange: null,
      addEventListener: (_type: string, listener: (event: MediaQueryListEvent) => void) =>
        expandedWindow.listeners.add(listener),
      removeEventListener: (_type: string, listener: (event: MediaQueryListEvent) => void) =>
        expandedWindow.listeners.delete(listener),
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => true,
    } as unknown as MediaQueryList;
  };
  return () => {
    window.matchMedia = realMatchMedia;
  };
}

function crossToExpanded() {
  expandedWindow.matches = true;
  for (const listener of expandedWindow.listeners) {
    listener({ matches: true, media: EXPANDED_QUERY } as MediaQueryListEvent);
  }
}

export const DrawerClosesAtExpandedWidth: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  args: {} as never,
  beforeEach: fakeExpandedQuery,
  render: () => <Harness />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const portal = portalQueries(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "Open navigation menu" }));
    await portal.findByRole("dialog");
    crossToExpanded();
    await waitFor(() => expect(portal.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(canvas.getByRole("main")).toHaveFocus());
  },
};
