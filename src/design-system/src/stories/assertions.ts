import { expect } from "storybook/test";

export function expectNoHorizontalPageScroll(canvasElement: HTMLElement): void {
  const root = canvasElement.ownerDocument.documentElement;
  expect(root.scrollWidth).toBeLessThanOrEqual(root.clientWidth);
}
