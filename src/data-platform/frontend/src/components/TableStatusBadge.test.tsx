import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TableStatusBadge } from "./TableStatusBadge";

describe("TableStatusBadge", () => {
  it("shows managed as the theme-colour category, with its text", () => {
    render(<TableStatusBadge status="managed" />);

    const badge = screen.getByText("Managed");
    expect(badge).toHaveClass("bg-inverse-primary");
    expect(badge).not.toHaveClass("bg-positive-container");
  });

  it("shows unmanaged as the neutral category", () => {
    render(<TableStatusBadge status="unmanaged" />);

    expect(screen.getByText("Unmanaged")).toHaveClass("bg-surface-container-dim");
  });

  it("shows dropped struck through and italic, with its text", () => {
    render(<TableStatusBadge status="dropped" />);

    const badge = screen.getByText("Dropped");
    expect(badge).toHaveClass("line-through");
    expect(badge).toHaveClass("italic!");
  });

  it("reads the status case-insensitively and keeps an unknown status as neutral text", () => {
    render(<TableStatusBadge status="MANAGED" />);
    render(<TableStatusBadge status="archived" />);

    expect(screen.getByText("Managed")).toHaveClass("bg-inverse-primary");
    expect(screen.getByText("Archived")).toHaveClass("bg-surface-container-dim");
  });
});
