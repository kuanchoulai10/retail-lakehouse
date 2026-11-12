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

  it("explains a table the discovery rules do not include and links to them", () => {
    renderReason("unmanaged");
    expect(screen.getByText("the discovery rules do not include this table")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Discovery rules" })).toHaveAttribute("href", "/discovery-rules");
  });

  it("explains a table recorded as dropped", () => {
    renderReason("dropped");
    expect(screen.getByText("maintenance recorded this table as dropped")).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
