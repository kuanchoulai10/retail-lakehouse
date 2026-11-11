import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { GlobListField } from "./GlobListField";

function Harness({ initial }: { initial: string[] }) {
  const [globs, setGlobs] = useState(initial);
  return (
    <>
      <GlobListField label="Tables" hint="Globs on the table name." globs={globs} onChange={setGlobs} />
      <output data-testid="value">{JSON.stringify(globs)}</output>
    </>
  );
}

const value = () => JSON.parse(screen.getByTestId("value").textContent ?? "[]") as string[];

describe("GlobListField", () => {
  it("shows each glob as a chip", () => {
    render(<Harness initial={["tmp_*", "staging_*"]} />);
    expect(screen.getByText("tmp_*")).toBeInTheDocument();
    expect(screen.getByText("staging_*")).toBeInTheDocument();
  });

  it("adds a glob on Enter and on Add", async () => {
    const user = userEvent.setup();
    render(<Harness initial={[]} />);
    await user.type(screen.getByRole("textbox", { name: "New tables glob" }), "orders_*{Enter}");
    await user.type(screen.getByRole("textbox", { name: "New tables glob" }), " events ");
    await user.click(screen.getByRole("button", { name: "Add tables glob" }));
    expect(value()).toEqual(["orders_*", "events"]);
  });

  it("adds what was typed when focus leaves the input", async () => {
    const user = userEvent.setup();
    render(<Harness initial={["a"]} />);
    await user.type(screen.getByRole("textbox", { name: "New tables glob" }), "b");
    await user.tab();
    expect(value()).toEqual(["a", "b"]);
  });

  it("ignores a blank or repeated glob", async () => {
    const user = userEvent.setup();
    render(<Harness initial={["a"]} />);
    await user.type(screen.getByRole("textbox", { name: "New tables glob" }), "a{Enter}   {Enter}");
    expect(value()).toEqual(["a"]);
  });

  it("removes a chip", async () => {
    const user = userEvent.setup();
    render(<Harness initial={["tmp_*", "staging_*"]} />);
    await user.click(screen.getByRole("button", { name: "Remove tables glob tmp_*" }));
    expect(value()).toEqual(["staging_*"]);
  });
});
