import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import { expectFocusRing, expectNoHorizontalPageScroll } from "../../stories/assertions";
import { TabItem, TabList, TabPanel, Tabs } from "./Tabs";

const meta = {
  title: "Components/Tabs",
  component: Tabs,
  parameters: {
    docs: {
      description: {
        component:
          "Expanded departs from Serendie: tabs are 36px high (44px below 768px and under a " +
          "coarse pointer). The tab list scrolls horizontally when it overflows.",
      },
    },
  },
} satisfies Meta<typeof Tabs>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <Tabs defaultValue="runs">
      <TabList aria-label="Table sections">
        <TabItem value="overview">Overview</TabItem>
        <TabItem value="runs">Runs</TabItem>
        <TabItem value="settings">Settings</TabItem>
      </TabList>
      <TabPanel value="overview">Overview content</TabPanel>
      <TabPanel value="runs">Runs content</TabPanel>
      <TabPanel value="settings">Settings content</TabPanel>
    </Tabs>
  ),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const [overview, runs, settings] = canvas.getAllByRole("tab") as [HTMLElement, HTMLElement, HTMLElement];
    await expect(runs).toHaveAttribute("aria-selected", "true");
    await userEvent.tab();
    await expectFocusRing(runs);
    await userEvent.keyboard("{ArrowRight}");
    await expectFocusRing(settings);
    await expect(settings).toHaveAttribute("aria-selected", "true");
    await expect(canvas.getByRole("tabpanel")).toHaveTextContent("Settings content");
    await userEvent.keyboard("{ArrowRight}");
    await expectFocusRing(overview);
    await userEvent.keyboard("{End}");
    await expectFocusRing(settings);
    await userEvent.keyboard("{Home}");
    await expectFocusRing(overview);
    await userEvent.keyboard("{ArrowLeft}");
    await expectFocusRing(settings);
  },
};

export const Overflowing: Story = {
  globals: { viewport: { value: "phone", isRotated: false } },
  render: () => (
    <Tabs defaultValue="t0">
      <TabList aria-label="Many sections">
        {Array.from({ length: 8 }, (_, index) => (
          <TabItem key={index} value={`t${index}`}>
            {`Section number ${index}`}
          </TabItem>
        ))}
      </TabList>
      <TabPanel value="t0">First</TabPanel>
    </Tabs>
  ),
  play: async ({ canvasElement }) => {
    const list = within(canvasElement).getByRole("tablist");
    await expect(list.scrollWidth).toBeGreaterThan(list.clientWidth);
    await expectNoHorizontalPageScroll(canvasElement);
  },
};
