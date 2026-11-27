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
  it.each([
    ["catalog-not-scanned", "no discovery policy in this catalog manages tables"],
    ["catalog-cannot-access", "discovery cannot read this catalog with the platform's catalog credential"],
    ["not-found", "discovery has not found this table yet"],
    ["unmanaged", "no discovery policy that applies to this table manages it"],
  ] as const)("explains %s and links to the discovery policies", (reason, message) => {
    renderReason(reason);
    expect(screen.getByText(message)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Discovery policies" })).toHaveAttribute("href", "/discovery-policies");
  });

  it("explains a table recorded as dropped", () => {
    renderReason("dropped");
    expect(screen.getByText("maintenance recorded this table as dropped")).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
