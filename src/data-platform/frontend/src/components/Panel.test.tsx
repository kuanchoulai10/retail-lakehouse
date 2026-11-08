import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Panel } from "@retail-lakehouse/design-system";

describe("Panel", () => {
  it("is a named region", () => {
    render(<Panel title="Health">body</Panel>);
    expect(screen.getByRole("region", { name: "Health" })).toBeInTheDocument();
  });
});
