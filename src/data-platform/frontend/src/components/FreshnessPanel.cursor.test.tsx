import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { FreshnessPanel } from "./FreshnessPanel";

const tooltipProps = vi.hoisted(() => [] as Record<string, unknown>[]);

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  BarChart: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  Bar: () => null,
  CartesianGrid: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: (props: Record<string, unknown>) => {
    tooltipProps.push(props);
    return null;
  },
}));

describe("FreshnessPanel tooltip", () => {
  // A hover cursor would paint behind the bars and drop chart colours below 3:1, so there is none.
  it("draws no hover cursor behind the bars", () => {
    render(<FreshnessPanel commits={[]} truncated={false} now={new Date()} lastCommittedAt={null} />);
    expect(tooltipProps.length).toBeGreaterThan(0);
    expect(tooltipProps.at(-1)?.cursor).toBe(false);
  });
});
