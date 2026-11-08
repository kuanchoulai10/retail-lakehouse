import { cn } from "./cn";

it("merges conflicting tailwind classes, last wins", () => {
  expect(cn("px-2 text-sm", undefined, false, "px-4")).toBe("text-sm px-4");
});
