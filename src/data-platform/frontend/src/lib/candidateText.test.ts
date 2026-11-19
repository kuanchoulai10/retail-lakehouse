import { describe, expect, it } from "vitest";
import type { CompactionCandidateApiResponse } from "@/api/generated/model";
import { formatTimestamp } from "@/format";
import { overdueText, roundPath, whyNotPicked } from "./candidateText";

const ROUND_ID = "cr-01m7acesg0fabv7jf1pza0mv4e";
const UNLISTED_ROUND_ID = "cr-01m79a0g20fyg9rjvt5yegdse3";

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
    granted_round_started_at: null,
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

  it("says a pending partition below the top N waits for a later round", () => {
    expect(whyNotPicked(candidate({ rank: 11 }), 10)).toBe("Waiting for a later round: below the top 10 (10 per table per round)");
  });

  it("says a pending partition in the top N waits for the next round", () => {
    expect(whyNotPicked(candidate({ rank: 10 }), 10)).toBe("Waiting for the next round");
  });

  it("names the round that granted a partition by its start time, as the rounds list does", () => {
    expect(
      whyNotPicked(
        candidate({
          state: "granted",
          rank: null,
          granted_round_id: ROUND_ID,
          granted_round_started_at: "2026-11-13T12:00:03Z",
        }),
        10,
      ),
    ).toBe(`Granted in round ${formatTimestamp("2026-11-13T12:00:03Z")}`);
  });

  it("says a partition was granted when its round is no longer listed", () => {
    expect(
      whyNotPicked(candidate({ state: "granted", rank: null, granted_round_id: UNLISTED_ROUND_ID }), 10),
    ).toBe("Granted");
  });

  it("says a partition held as not due waits for the table's compaction to be due", () => {
    expect(whyNotPicked(candidate({ state: "held", hold_reason: "not_due", rank: null }), 10)).toBe(
      "Compaction is not due on this table",
    );
  });

  it("says a partition held in cooldown keeps waiting for a round", () => {
    expect(whyNotPicked(candidate({ state: "held", hold_reason: "cooldown", rank: null }), 10)).toBe(
      "Compaction is cooling down on this table; its wait for a round goes on",
    );
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

describe("roundPath", () => {
  it("opens the rounds page at the round", () => {
    expect(roundPath(ROUND_ID)).toBe(`/compaction-rounds?round=${ROUND_ID}`);
  });
});

describe("overdueText", () => {
  const now = new Date("2026-11-13T12:00:00Z");

  it("says how long the partition waited and how long its priority allows", () => {
    expect(overdueText(candidate({ priority: "P0", pending_since: "2026-11-13T09:00:00Z" }), 3600, now)).toBe(
      "Waited 3 h; P0 allows 1 h",
    );
  });

  it("counts a short wait in minutes and a long one in days", () => {
    expect(overdueText(candidate({ priority: "P0", pending_since: "2026-11-13T11:15:00Z" }), 1800, now)).toBe(
      "Waited 45 min; P0 allows 30 min",
    );
    expect(overdueText(candidate({ pending_since: "2026-11-10T11:00:00Z" }), 28_800, now)).toBe(
      "Waited 3 d; P2 allows 8 h",
    );
  });

  it("says only that the wait is longer than the priority allows before the settings load", () => {
    expect(overdueText(candidate({ pending_since: "2026-11-13T09:00:00Z" }), undefined, now)).toBe(
      "Waited 3 h, longer than P2 allows",
    );
  });

  it("says why without a wait when the candidate has none", () => {
    expect(overdueText(candidate({ pending_since: null }), 28_800, now)).toBe("Waited longer than P2 allows (8 h)");
  });
});
