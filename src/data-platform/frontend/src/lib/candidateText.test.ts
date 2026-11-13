import { describe, expect, it } from "vitest";
import type { CompactionCandidateApiResponse } from "@/api/generated/model";
import { whyNotPicked } from "./candidateText";

function candidate(overrides: Partial<CompactionCandidateApiResponse>): CompactionCandidateApiResponse {
  return {
    partition: { spec_id: 0, values: ["2026-11-01"] },
    partition_label: "day=2026-11-01",
    state: "pending",
    hold_reason: null,
    reducible_files: 12,
    data_bytes: 4096,
    estimated_gb_hours: 0.25,
    score: 48,
    rank: 1,
    claimed_by_run_id: null,
    lease_expires_at: null,
    last_written_at: null,
    observed_at: "2026-11-13T09:00:00Z",
    priority: "P2",
    granted_round_id: null,
    pending_since: null,
    overdue: false,
    ...overrides,
  };
}

describe("whyNotPicked", () => {
  it("says a held partition is too small", () => {
    expect(whyNotPicked(candidate({ state: "held", hold_reason: "too_small", rank: null }), 10)).toBe(
      "Too small to be worth compacting",
    );
  });

  it("says a held partition is still being written", () => {
    expect(whyNotPicked(candidate({ state: "held", hold_reason: "recently_written", rank: null }), 10)).toBe(
      "Still being written; checked again after a quiet period",
    );
  });

  it("says a pending partition below the top N lost on score", () => {
    expect(whyNotPicked(candidate({ rank: 11 }), 10)).toBe("Score below the top 10 (10 per run)");
  });

  it("says nothing against a pending partition in the top N", () => {
    expect(whyNotPicked(candidate({ rank: 10 }), 10)).toBe("");
  });

  it.each(["claimed", "running"])("names the run that holds a %s partition", (state) => {
    expect(whyNotPicked(candidate({ state, rank: null, claimed_by_run_id: "run-7" }), 10)).toBe("In run run-7");
  });

  it.each(["done", "failed"])("says a %s partition waits for the next observation", (state) => {
    expect(whyNotPicked(candidate({ state, rank: null }), 10)).toBe("Waiting for the next observation");
  });

  it("reads an unknown hold reason in words", () => {
    expect(whyNotPicked(candidate({ state: "held", hold_reason: "frozen_by_owner", rank: null }), 10)).toBe(
      "Held: frozen by owner",
    );
  });
});
