import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { ThemeProvider } from "../theme/ThemeProvider";
import { AppShell } from "./AppShell";

function renderShell() {
  return render(
    <ThemeProvider>
      <MemoryRouter>
        <AppShell>
          <p>Page body</p>
        </AppShell>
      </MemoryRouter>
    </ThemeProvider>,
  );
}

describe("AppShell", () => {
  it("renders a navigation landmark with a Tables link to the list", () => {
    renderShell();
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(within(nav).getByRole("link", { name: "Tables" })).toHaveAttribute("href", "/");
  });

  it("links the product name to the list", () => {
    renderShell();
    const brands = screen.getAllByRole("link", { name: "Lakehouse" });
    expect(brands.length).toBeGreaterThan(0);
    for (const brand of brands) {
      expect(brand).toHaveAttribute("href", "/");
    }
  });

  it("renders its children in the main landmark", () => {
    renderShell();
    expect(within(screen.getByRole("main")).getByText("Page body")).toBeInTheDocument();
  });
});
