import { render } from "@testing-library/react";
import * as icons from "./index";

const ICONS = Object.entries(icons).filter(([name]) => name.startsWith("Icon"));

describe("icons", () => {
  it.each(ICONS)("%s draws a 1.5 stroke by default", (_name, Icon) => {
    const { container } = render(<Icon />);
    expect(container.querySelector("svg")?.getAttribute("stroke-width")).toBe("1.5");
  });

  it("keeps a stroke a caller sets", () => {
    const { container } = render(<icons.IconCheck stroke={2} />);
    expect(container.querySelector("svg")?.getAttribute("stroke-width")).toBe("2");
  });
});
