import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { Breadcrumbs } from "./Breadcrumbs";

describe("Breadcrumbs", () => {
  it("every crumb but the last is a link", () => {
    render(
      <MemoryRouter>
        <Breadcrumbs
          crumbs={[
            { label: "Catalogs", to: "/catalogs" },
            { label: "iceberg", to: "/catalogs/iceberg" },
            { label: "inventory", to: "/catalogs/iceberg/namespaces/inventory" },
          ]}
        />
      </MemoryRouter>,
    );
    expect(screen.getByRole("link", { name: "Catalogs" })).toHaveAttribute("href", "/catalogs");
    expect(screen.getByRole("link", { name: "iceberg" })).toHaveAttribute(
      "href",
      "/catalogs/iceberg",
    );
    expect(screen.queryByRole("link", { name: "inventory" })).not.toBeInTheDocument();
    expect(screen.getByText("inventory")).toHaveAttribute("aria-current", "page");
  });
});
