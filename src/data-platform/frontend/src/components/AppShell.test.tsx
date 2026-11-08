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
  it("renders a navigation landmark with a Tables link to the list", () => {
    renderShell();
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(within(nav).getByRole("link", { name: "Tables" })).toHaveAttribute("href", "/");
  });

  it("lists the four console sections in the main navigation", () => {
    renderShell();
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(within(nav).getAllByRole("link").map((link) => link.textContent)).toEqual([
      "Tables",
      "Catalog",
      "Presets",
      "Discovery rules",
    ]);
  });

  it("links the presets and discovery rules pages", () => {
    renderShell();
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(within(nav).getByRole("link", { name: "Presets" })).toHaveAttribute("href", "/presets");
    expect(within(nav).getByRole("link", { name: "Discovery rules" })).toHaveAttribute(
      "href",
      "/discovery-rules",
    );
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
    renderShell("/presets");
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(within(nav).getByRole("link", { name: "Presets" })).toHaveAttribute("aria-current", "page");
    expect(within(nav).getByRole("link", { name: "Tables" })).not.toHaveAttribute("aria-current");
  });

  it("shows the product name in the top app bar", () => {
    renderShell();
    expect(within(screen.getByRole("banner")).getByText("Lakehouse")).toBeInTheDocument();
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
