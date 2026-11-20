import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { VersionList } from "./VersionList";

function versions(count: number) {
  return Array.from({ length: count }, (_, index) => {
    const id = count - 1 - index;
    return { id, title: `v${id}`, description: id === 0 ? "First version" : "No changes", ...(id === 3 ? { badge: "Current" } : {}) };
  });
}

function titles(): string[] {
  return screen.getAllByRole("listitem").map((item) => item.querySelector("button")?.textContent ?? "");
}

describe("VersionList", () => {
  it("shows the newest ten and folds the rest behind a button", async () => {
    const user = userEvent.setup();
    render(<VersionList label="Schema versions" versions={versions(12)} selectedId={11} onSelect={vi.fn()} />);
    expect(screen.getAllByRole("listitem")).toHaveLength(10);
    expect(screen.getByRole("list", { name: "Schema versions" })).toBeInTheDocument();
    expect(screen.queryByText("v1")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show 2 earlier versions" }));
    expect(screen.getAllByRole("listitem")).toHaveLength(12);
    expect(screen.getByText("v0")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /earlier version/ })).not.toBeInTheDocument();
  });

  it("starts expanded when the selected version is one of the folded ones", () => {
    render(<VersionList label="Schema versions" versions={versions(12)} selectedId={0} onSelect={vi.fn()} />);
    expect(screen.getAllByRole("listitem")).toHaveLength(12);
    expect(screen.queryByRole("button", { name: /earlier version/ })).not.toBeInTheDocument();
  });

  it("marks the selected version and shows its badge and description", () => {
    render(<VersionList label="Schema versions" versions={versions(4)} selectedId={3} onSelect={vi.fn()} />);
    const [newest] = screen.getAllByRole("listitem");
    expect(newest?.querySelector("button")).toHaveAttribute("aria-current", "true");
    expect(newest).toHaveTextContent("v3");
    expect(newest).toHaveTextContent("Current");
    expect(screen.getByText("First version")).toBeInTheDocument();
    expect(titles()).toHaveLength(4);
    expect(screen.queryByRole("button", { name: /earlier version/ })).not.toBeInTheDocument();
  });

  it("selects with Enter and reaches the fold button with Tab", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<VersionList label="Schema versions" versions={versions(12)} selectedId={11} onSelect={onSelect} />);
    await user.tab();
    expect(screen.getAllByRole("listitem")[0]?.querySelector("button")).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(onSelect).toHaveBeenCalledWith(11);
    for (let step = 0; step < 10; step += 1) await user.tab();
    const fold = screen.getByRole("button", { name: "Show 2 earlier versions" });
    expect(fold).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(screen.getAllByRole("listitem")).toHaveLength(12);
    expect(screen.getAllByRole("listitem")[10]?.querySelector("button")).toHaveFocus();
  });
});
