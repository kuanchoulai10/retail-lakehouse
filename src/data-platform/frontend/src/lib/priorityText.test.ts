import { describe, expect, it } from "vitest";
import type { SchedulerPriorityApiResponse } from "@/api/generated/model";
import { priorityText, priorityWeightsText } from "./priorityText";

const PRIORITIES: SchedulerPriorityApiResponse[] = [
  { priority: "P0", weight: 4, sla_seconds: 3600 },
  { priority: "P1", weight: 2, sla_seconds: 14_400 },
  { priority: "P2", weight: 1, sla_seconds: 28_800 },
];

describe("priorityText", () => {
  it("says within how long a priority is compacted", () => {
    expect(priorityText("P2", PRIORITIES)).toBe("P2 (within 8 h)");
    expect(priorityText("P0", PRIORITIES)).toBe("P0 (within 1 h)");
  });

  it("shows the priority alone before the settings load", () => {
    expect(priorityText("P1", undefined)).toBe("P1");
  });

  it("shows a priority the settings do not know alone", () => {
    expect(priorityText("P9", PRIORITIES)).toBe("P9");
  });
});

describe("priorityWeightsText", () => {
  it("lists each priority's weight", () => {
    expect(priorityWeightsText(PRIORITIES)).toBe("P0 × 4, P1 × 2, P2 × 1");
  });
});
