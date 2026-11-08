import { describe, expect, it } from "vitest";
import { statusTone } from "./statusTone";

describe("statusTone", () => {
  it.each([
    ["succeeded", "positive"],
    ["SUCCEEDED", "positive"],
    ["failed", "negative"],
    ["error", "negative"],
    ["due", "notice"],
    ["truncated", "notice"],
    ["active", "neutral"],
    ["paused", "neutral"],
    ["running", "neutral"],
  ])("maps %s to %s", (status, tone) => {
    expect(statusTone(status)).toBe(tone);
  });
});
