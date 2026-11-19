import { CHART_COLOURS } from "../../components/ChartContainer/ChartContainer";

export function seriesColour(position: number): string {
  return CHART_COLOURS[position % CHART_COLOURS.length] as string;
}
