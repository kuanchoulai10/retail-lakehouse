import { expect, userEvent, waitFor, within } from "storybook/test";

export async function expectNoHorizontalPageScroll(canvasElement: HTMLElement): Promise<void> {
  const root = canvasElement.ownerDocument.documentElement;
  await expect(root.scrollWidth).toBeLessThanOrEqual(root.clientWidth);
}

export async function expectFocusRing(element: HTMLElement): Promise<void> {
  await expect(element).toHaveFocus();
  await expect(getComputedStyle(element).outlineWidth).not.toBe("0px");
}

export function portalQueries(canvasElement: HTMLElement) {
  return within(canvasElement.ownerDocument.body);
}

export async function exerciseOverlay(
  canvasElement: HTMLElement,
  triggerName: string,
  role: "dialog" | "alertdialog",
): Promise<void> {
  const trigger = within(canvasElement).getByRole("button", { name: triggerName });
  await userEvent.tab();
  await expectFocusRing(trigger);
  await userEvent.keyboard("{Enter}");
  const overlay = await portalQueries(canvasElement).findByRole(role);
  await waitFor(() => expect(overlay).toContainElement(document.activeElement as HTMLElement));
  for (let press = 0; press < 6; press += 1) {
    await userEvent.tab();
    await expect(overlay).toContainElement(document.activeElement as HTMLElement);
  }
  await userEvent.keyboard("{Escape}");
  await waitFor(() => expect(portalQueries(canvasElement).queryByRole(role)).toBeNull());
  await waitFor(() => expect(trigger).toHaveFocus());
}
