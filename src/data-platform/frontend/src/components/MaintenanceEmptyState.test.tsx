import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { MaintenanceEmptyState } from "./MaintenanceEmptyState";

function renderReason(reason: React.ComponentProps<typeof MaintenanceEmptyState>["reason"]) {
  render(
    <MemoryRouter>
      <MaintenanceEmptyState reason={reason} />
    </MemoryRouter>,
  );
}

describe("MaintenanceEmptyState", () => {
  it("explains a catalog maintenance does not cover", () => {
    renderReason("catalog-not-covered");
    expect(screen.getByText("this catalog is not covered by maintenance")).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("links to discovery rules when no rule includes the table", () => {
    renderReason("not-found");
    expect(screen.getByText("no discovery rule includes this table")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Discovery rules" })).toHaveAttribute(
      "href",
      "/discovery-rules",
    );
  });

  it("explains a table excluded by hand", () => {
    renderReason("excluded");
    expect(screen.getByText("excluded from maintenance by hand")).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("explains a table recorded as dropped", () => {
    renderReason("dropped");
    expect(screen.getByText("maintenance recorded this table as dropped")).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
