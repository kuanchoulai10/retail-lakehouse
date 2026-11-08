import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, waitFor, within } from "storybook/test";
import { ThemeProvider } from "../../theme/ThemeProvider";
import { expectFocusRing, portalQueries } from "../../stories/assertions";
import { ThemePicker } from "./ThemePicker";

const meta = {
  title: "Components/ThemePicker",
  component: ThemePicker,
  decorators: [
    (Story) => (
      <ThemeProvider>
        <div className="h-64 p-4">
          <Story />
        </div>
      </ThemeProvider>
    ),
  ],
  parameters: {
    docs: {
      description: {
        component: "Not in Serendie. A radio menu over the three themes; the choice is remembered.",
      },
    },
  },
} satisfies Meta<typeof ThemePicker>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const trigger = within(canvasElement).getByRole("button", { name: "Colour theme: Konjo" });
    await userEvent.tab();
    await expectFocusRing(trigger);
    await userEvent.keyboard("{Enter}");
    const portal = portalQueries(canvasElement);
    await portal.findByRole("menu");
    await userEvent.keyboard("{ArrowDown}");
    await expect(portal.getByRole("menuitemradio", { name: "Asagi" })).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    await waitFor(() =>
      expect(document.documentElement).toHaveAttribute("data-panda-theme", "asagi"),
    );
    await waitFor(() => expect(trigger).toHaveFocus());
    await expect(trigger).toHaveAccessibleName("Colour theme: Asagi");
    await userEvent.keyboard("{Enter}");
    await portal.findByRole("menu");
    await expect(portal.getByRole("menuitemradio", { name: "Asagi" })).toBeChecked();
    await userEvent.click(portal.getByRole("menuitemradio", { name: "Konjo" }));
    await waitFor(() =>
      expect(document.documentElement).not.toHaveAttribute("data-panda-theme"),
    );
  },
};
