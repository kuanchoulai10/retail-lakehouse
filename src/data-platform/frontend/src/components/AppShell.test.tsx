import { ThemeProvider } from "@retail-lakehouse/design-system";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it } from "vitest";
import { AppShell } from "./AppShell";

function renderShell(path = "/") {
  return render(
    <ThemeProvider>
      <MemoryRouter initialEntries={[path]}>
        <AppShell>
          <p>Page body</p>
        </AppShell>
      </MemoryRouter>
    </ThemeProvider>,
  );
}

afterEach(() => {
  document.documentElement.removeAttribute("data-panda-theme");
  localStorage.clear();
});

describe("AppShell", () => {
  it("links the platform settings page, last, and marks it current there", () => {
    renderShell("/platform-settings");
    const nav = screen.getByRole("navigation", { name: "Main" });
    const links = within(nav).getAllByRole("link");
    expect(links.at(-1)).toHaveTextContent("Platform settings");
    expect(links.at(-1)).toHaveAttribute("href", "/platform-settings");
    expect(links.at(-1)).toHaveAttribute("aria-current", "page");
  });

  it("renders a navigation landmark with a Tables link to the list", () => {
    renderShell();
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(within(nav).getByRole("link", { name: "Tables" })).toHaveAttribute("href", "/");
  });

  it("lists the console sections in the main navigation", () => {
    renderShell();
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(within(nav).getAllByRole("link").map((link) => link.textContent)).toEqual([
      "Tables",
      "Catalog",
      "Discovery policies",
      "Maintenance policies",
      "Platform settings",
    ]);
  });

  it("links the policies page and marks it current there", () => {
    renderShell("/policies");
    const nav = screen.getByRole("navigation", { name: "Main" });
    const link = within(nav).getByRole("link", { name: "Maintenance policies" });
    expect(link).toHaveAttribute("href", "/policies");
    expect(link).toHaveAttribute("aria-current", "page");
  });

  it("links the discovery policies page and marks it current on a policy's page", () => {
    renderShell("/discovery-policies/sales-tables");
    const nav = screen.getByRole("navigation", { name: "Main" });
    const link = within(nav).getByRole("link", { name: "Discovery policies" });
    expect(link).toHaveAttribute("href", "/discovery-policies");
    expect(link).toHaveAttribute("aria-current", "page");
  });

  it("links the catalog and marks it current under /catalogs/*", () => {
    renderShell("/catalogs/iceberg/namespaces/a.b%1Fc");
    const nav = screen.getByRole("navigation", { name: "Main" });
    const link = within(nav).getByRole("link", { name: "Catalog" });
    expect(link).toHaveAttribute("href", "/catalogs");
    expect(link).toHaveAttribute("aria-current", "page");
    expect(within(nav).getByRole("link", { name: "Tables" })).not.toHaveAttribute("aria-current");
  });

  it("marks only the current section as the current page", () => {
    renderShell("/discovery-policies");
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(within(nav).getByRole("link", { name: "Discovery policies" })).toHaveAttribute("aria-current", "page");
    expect(within(nav).getByRole("link", { name: "Tables" })).not.toHaveAttribute("aria-current");
  });

  it("puts the theme picker beside the product name, not at the end of the top app bar", () => {
    renderShell();
    const banner = within(screen.getByRole("banner"));
    const product = banner.getByRole("link", { name: "Lakehouse" });
    const picker = banner.getByRole("button", { name: /Colour theme/ });
    expect(product.compareDocumentPosition(picker) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(picker.parentElement?.nextElementSibling?.className).toContain("flex-1");
  });

  it("shows the product name in the top app bar", () => {
    renderShell();
    expect(within(screen.getByRole("banner")).getByText("Lakehouse")).toBeInTheDocument();
  });

  it("links the product name to the list", () => {
    renderShell();
    const brands = screen.getAllByRole("link", { name: "Lakehouse" });
    expect(brands.length).toBeGreaterThan(0);
    for (const brand of brands) {
      expect(brand).toHaveAttribute("href", "/");
    }
  });

  it("puts the colour theme picker in the top app bar and applies the picked theme", async () => {
    const user = userEvent.setup();
    renderShell();
    const banner = screen.getByRole("banner");
    await user.click(within(banner).getByRole("button", { name: /^Colour theme/ }));
    await user.click(await screen.findByRole("menuitemradio", { name: "Asagi" }));
    expect(document.documentElement).toHaveAttribute("data-panda-theme", "asagi");
    expect(within(banner).getByRole("button", { name: "Colour theme: Asagi" })).toBeInTheDocument();
  });

  it("renders its children in the main landmark", () => {
    renderShell();
    expect(within(screen.getByRole("main")).getByText("Page body")).toBeInTheDocument();
  });
});
