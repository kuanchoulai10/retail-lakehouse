import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { expect, fn, waitFor, within } from "storybook/test";
import { applyTheme } from "../../theme/applyTheme";
import {
  exerciseOverlay,
  expectNoHorizontalPageScroll,
  portalQueries,
} from "../../stories/assertions";
import { Button } from "../Button/Button";
import { TextField } from "../TextField/TextField";
import { ModalDialog } from "./ModalDialog";

const meta = {
  title: "Components/ModalDialog",
  component: ModalDialog,
  args: {
    isOpen: false,
    onOpenChange: fn(),
    title: "Edit preset",
    description: "Changes apply to every table that uses this preset.",
    children: <TextField label="Preset name" />,
  },
  parameters: {
    docs: {
      description: {
        component:
          "Expanded departs from Serendie: a centred 512px panel with 36px controls; below " +
          "768px it is a full-screen sheet with 44px controls.",
      },
    },
  },
} satisfies Meta<typeof ModalDialog>;

export default meta;

type Story = StoryObj<typeof meta>;

function Harness(props: Partial<React.ComponentProps<typeof ModalDialog>>) {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <div className="p-4">
      <Button onClick={() => setIsOpen(true)}>Open dialog</Button>
      <ModalDialog
        title="Edit preset"
        description="Changes apply to every table that uses this preset."
        isOpen={isOpen}
        onOpenChange={setIsOpen}
        footer={
          <>
            <Button styleType="ghost" onClick={() => setIsOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => setIsOpen(false)}>Save</Button>
          </>
        }
        {...props}
      >
        <TextField label="Preset name" />
      </ModalDialog>
    </div>
  );
}

export const Default: Story = {
  render: () => <Harness />,
  play: async ({ canvasElement }) => {
    await exerciseOverlay(canvasElement, "Open dialog", "dialog");
  },
};

export const WithoutDescription: Story = {
  render: () => <Harness description={undefined} />,
  play: async ({ canvasElement }) => {
    await exerciseOverlay(canvasElement, "Open dialog", "dialog");
  },
};

export const Touch: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  args: { isOpen: true },
  play: async ({ canvasElement }) => {
    const dialog = await portalQueries(canvasElement).findByRole("dialog");
    const rect = dialog.getBoundingClientRect();
    await expect(rect.width).toBe(window.innerWidth);
    await expect(rect.height).toBe(window.innerHeight);
    await expectNoHorizontalPageScroll(canvasElement);
  },
};

export const Desktop: Story = {
  globals: { viewport: { value: "desktop", isRotated: false } },
  args: { isOpen: true },
  play: async ({ canvasElement }) => {
    const dialog = await portalQueries(canvasElement).findByRole("dialog");
    const rect = dialog.getBoundingClientRect();
    await expect(rect.width).toBeLessThanOrEqual(512);
    await expect(rect.left).toBeGreaterThan(0);
  },
};

function resolveColor(value: string): string {
  const probe = document.createElement("div");
  probe.style.backgroundColor = value;
  document.body.appendChild(probe);
  const resolved = getComputedStyle(probe).backgroundColor;
  probe.remove();
  return resolved;
}

export const FollowsThemeSwitch: Story = {
  args: { isOpen: true, footer: <Button>Save</Button> },
  play: async ({ canvasElement }) => {
    const root = document.documentElement;
    const token = (name: string) => resolveColor(getComputedStyle(root).getPropertyValue(name));
    const dialog = await within(document.body).findByRole("dialog");
    const save = within(dialog).getByRole("button", { name: "Save" });
    const background = () => getComputedStyle(dialog).backgroundColor;
    const buttonBackground = () => getComputedStyle(save).backgroundColor;

    const konjoSurface = token("--ds-surface");
    const konjoPrimary = token("--ds-primary-container");
    await waitFor(() => expect(background()).toBe(konjoSurface));
    await waitFor(() => expect(buttonBackground()).toBe(konjoPrimary));

    applyTheme(root, "kurikawa");
    const kurikawaSurface = token("--ds-surface");
    const kurikawaPrimary = token("--ds-primary-container");
    await waitFor(() => expect(background()).toBe(kurikawaSurface));
    await waitFor(() => expect(buttonBackground()).toBe(kurikawaPrimary));
    await expect(kurikawaPrimary).not.toBe(konjoPrimary);
    if (kurikawaSurface !== konjoSurface) {
      await expect(background()).not.toBe(konjoSurface);
    }
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
