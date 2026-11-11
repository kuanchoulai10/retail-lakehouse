import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { OperationPolicySection, type TriggerCondition } from "./OperationPolicySection";

function field(label: string, value = "") {
  return { label, value, onChange: vi.fn() };
}

function renderSection(conditions: TriggerCondition[], scope?: { value: "partition" | "table"; onChange: () => void }) {
  const onEnabledChange = vi.fn();
  render(
    <OperationPolicySection
      title="Rewrite manifests"
      enabled
      onEnabledChange={onEnabledChange}
      scope={scope}
      cooldown={field("Cooldown (seconds)", "3600")}
      conditions={conditions}
    >
      <p>Execution fields</p>
    </OperationPolicySection>,
  );
  return { onEnabledChange };
}

function triggerGroup(): HTMLElement {
  return within(screen.getByRole("group", { name: "Rewrite manifests" })).getByRole("group", { name: "Trigger" });
}

describe("OperationPolicySection", () => {
  it("lists the conditions of the trigger group separated by the word or", () => {
    renderSection([
      { label: "Small manifests", fields: [field("Small manifests at least", "5"), field("Smaller than (bytes)")] },
      { label: "Reducible files", fields: [field("Reducible files at least")] },
      { label: "Expirable snapshots", fields: [field("Expirable snapshots at least")] },
    ]);
    const trigger = triggerGroup();
    const conditions = within(trigger).getAllByRole("group");
    expect(conditions.map((group) => group.getAttribute("aria-label"))).toEqual([
      "Small manifests",
      "Reducible files",
      "Expirable snapshots",
    ]);
    const separators = within(trigger).getAllByText("or", { exact: true });
    expect(separators).toHaveLength(2);
    expect(conditions[0]?.nextElementSibling).toBe(separators[0]);
    expect(separators[0]?.nextElementSibling).toBe(conditions[1]);
    expect(within(conditions[0]!).getByRole("spinbutton", { name: "Small manifests at least" })).toHaveValue(5);
  });

  it("shows the cooldown in the trigger group and the rest in the execution group", () => {
    renderSection([{ label: "Small manifests", fields: [field("Small manifests at least", "5")] }]);
    expect(within(triggerGroup()).getByRole("spinbutton", { name: "Cooldown (seconds)" })).toHaveValue(3600);
    expect(within(triggerGroup()).queryByText("or", { exact: true })).not.toBeInTheDocument();
    const execution = within(screen.getByRole("group", { name: "Rewrite manifests" })).getByRole("group", {
      name: "Execution",
    });
    expect(within(execution).getByText("Execution fields")).toBeInTheDocument();
  });

  it("says the cooldown alone decides when there are no conditions", () => {
    renderSection([]);
    expect(within(triggerGroup()).getByText("No conditions: due once the cooldown has passed.")).toBeInTheDocument();
  });

  it("switches the operation on and off", async () => {
    const user = userEvent.setup();
    const { onEnabledChange } = renderSection([]);
    const section = screen.getByRole("group", { name: "Rewrite manifests" });
    await user.click(within(section).getByRole("switch", { name: "Enabled" }));
    expect(onEnabledChange).toHaveBeenCalledWith(false);
  });

  it("shows a scope only when the operation has one", () => {
    renderSection([], { value: "partition", onChange: vi.fn() });
    expect(screen.getByRole("combobox", { name: "Scope" })).toHaveTextContent("Each partition");
  });

  it("has no scope when none is given", () => {
    renderSection([]);
    expect(screen.queryByRole("combobox", { name: "Scope" })).not.toBeInTheDocument();
  });
});
