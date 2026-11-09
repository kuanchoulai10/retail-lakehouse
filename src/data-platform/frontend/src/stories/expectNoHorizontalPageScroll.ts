import { expect } from "storybook/test";

// Phones count: a page never scrolls sideways; wide tables scroll inside their container.
export async function expectNoHorizontalPageScroll(canvasElement: HTMLElement): Promise<void> {
  const root = canvasElement.ownerDocument.documentElement;
  await expect(root.scrollWidth).toBeLessThanOrEqual(root.clientWidth);
}
