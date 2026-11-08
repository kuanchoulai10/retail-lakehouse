import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { SEMANTIC_TOKENS } from "../tokens/semanticTokens";
import { expectNoHorizontalPageScroll } from "./assertions";

const TYPE_ROLES = [
  "type-display-small",
  "type-headline-small",
  "type-title-large",
  "type-title-medium",
  "type-title-small",
  "type-body-large",
  "type-body-medium",
  "type-body-small",
  "type-label-large",
  "type-label-medium",
  "type-label-small",
  "type-code",
] as const;

function ColourSwatches() {
  return (
    <ul className="grid list-none grid-cols-2 gap-4 p-0 md:grid-cols-4">
      {SEMANTIC_TOKENS.map((token) => (
        <li key={token}>
          <figure className="m-0" aria-labelledby={`swatch-${token}`}>
            <div
              data-swatch={token}
              className="h-12 rounded-md border border-outline-dim"
              style={{ backgroundColor: `var(--ds-${token})` }}
            />
            <figcaption id={`swatch-${token}`} className="type-code mt-1 break-all text-on-surface">{token}</figcaption>
          </figure>
        </li>
      ))}
    </ul>
  );
}

function TypeRoles() {
  return (
    <div className="flex flex-col gap-4">
      {TYPE_ROLES.map((role) => (
        <p key={role} className={`${role} m-0 text-on-surface`}>
          {role}: Iceberg table maintenance
        </p>
      ))}
    </div>
  );
}

function DensitySamples() {
  return (
    <div className="flex flex-col gap-4 text-on-surface">
      <div className="type-label-large flex h-control items-center rounded-md border border-outline-dim px-3">
        h-control
      </div>
      <div className="type-body-medium flex min-h-row items-center border-b border-outline-dim px-3">
        min-h-row
      </div>
    </div>
  );
}

const meta = {
  title: "Foundations",
  parameters: { layout: "padded" },
} satisfies Meta;

export default meta;

type Story = StoryObj<typeof meta>;

export const Colours: Story = {
  render: () => <ColourSwatches />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    for (const token of SEMANTIC_TOKENS) {
      const figure = canvas.getByRole("figure", { name: token });
      const swatch = figure.querySelector<HTMLElement>(`[data-swatch="${token}"]`);
      await expect(swatch).not.toBeNull();
      await expect(getComputedStyle(swatch as HTMLElement).backgroundColor).not.toBe(
        "rgba(0, 0, 0, 0)",
      );
    }
    await expect(canvas.getAllByRole("figure")).toHaveLength(SEMANTIC_TOKENS.length);
    expectNoHorizontalPageScroll(canvasElement);
  },
};

export const Typography: Story = {
  render: () => <TypeRoles />,
};

export const Density: Story = {
  render: () => <DensitySamples />,
};
