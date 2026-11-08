import { contrastRatio } from "./contrastRatio";

it("matches WCAG reference values", () => {
  expect(contrastRatio("#000000", "#FFFFFF")).toBeCloseTo(21, 1);
  expect(contrastRatio("#2EAB80", "#FFFFFF")).toBeCloseTo(2.9, 1);
  expect(contrastRatio("#816E00", "#FFFFFF")).toBeCloseTo(5.04, 1);
});
