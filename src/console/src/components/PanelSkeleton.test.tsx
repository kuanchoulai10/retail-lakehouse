import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PanelSkeleton } from "./PanelSkeleton";

describe("PanelSkeleton", () => {
  it("announces what is loading", () => {
    render(<PanelSkeleton label="Loading storage…" />);
    expect(screen.getByText("Loading storage…")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "true");
  });
});
