import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { OperationPolicySection } from "./OperationPolicySection";

function renderSection(included = true) {
  const onIncludedChange = vi.fn();
  render(
    <OperationPolicySection
      title="Rewrite manifests"
      included={included}
      onIncludedChange={onIncludedChange}
      target={<p>Target fields</p>}
      options={<p>Option fields</p>}
    />,
  );
  return { onIncludedChange, section: screen.getByRole("group", { name: "Rewrite manifests" }) };
}

describe("OperationPolicySection", () => {
  it("shows the target and the options in their own groups", () => {
    const { section } = renderSection();
    expect(within(within(section).getByRole("group", { name: "Target" })).getByText("Target fields")).toBeInTheDocument();
    const options = within(section).getByRole("group", { name: "Options" });
    expect(within(options).getByText("Option fields")).toBeInTheDocument();
    expect(within(options).getByText("Empty: the procedure's default.")).toBeInTheDocument();
  });

  it("takes the operation in and out of the policy", async () => {
    const user = userEvent.setup();
    const { onIncludedChange, section } = renderSection();
    const toggle = within(section).getByRole("switch", { name: "In this policy" });
    expect(toggle).toBeChecked();
    await user.click(toggle);
    expect(onIncludedChange).toHaveBeenCalledWith(false);
  });

  it("hides the groups and says so when the operation is not in the policy", () => {
    const { section } = renderSection(false);
    expect(within(section).getByRole("switch", { name: "In this policy" })).not.toBeChecked();
    expect(
      within(section).getByText("Not in this policy: this operation does not run on a schedule."),
    ).toBeInTheDocument();
    expect(within(section).queryByRole("group", { name: "Target" })).not.toBeInTheDocument();
    expect(within(section).queryByRole("group", { name: "Options" })).not.toBeInTheDocument();
  });
});
