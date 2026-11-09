import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { TableCommitApiResponse } from "../api/generated/model";
import { FreshnessPanel } from "./FreshnessPanel";

const NOW = new Date("2026-11-01T12:00:00Z");

function commit(id: string, operation: string): TableCommitApiResponse {
  return {
    snapshot_id: id,
    parent_id: null,
    committed_at: "2026-11-01T11:30:00Z",
    operation,
    writer: "kafka_connect",
    added_records: null,
    deleted_records: null,
    added_data_files: null,
    deleted_data_files: null,
    added_delete_files: null,
    removed_delete_files: null,
    summary: {},
  };
}

describe("FreshnessPanel", () => {
  it("lists one legend entry per operation present in the buckets", () => {
    render(
      <FreshnessPanel
        commits={[commit("1", "append"), commit("2", "overwrite"), commit("3", "append")]}
        truncated={false}
        now={NOW}
        lastCommittedAt="2026-11-01T11:30:00Z"
      />,
    );
    const legend = screen.getByRole("list", { name: "Operations" });
    const entries = within(legend).getAllByRole("listitem");
    expect(entries.map((entry) => entry.textContent)).toEqual(["append", "overwrite"]);
  });

  it("shows no legend when there are no commits", () => {
    render(<FreshnessPanel commits={[]} truncated={false} now={NOW} lastCommittedAt={null} />);
    expect(screen.queryByRole("list", { name: "Operations" })).not.toBeInTheDocument();
  });

  it("marks truncated counts with the warning colour", () => {
    render(
      <FreshnessPanel
        commits={[commit("1", "append")]}
        truncated
        now={NOW}
        lastCommittedAt="2026-11-01T11:30:00Z"
      />,
    );
    expect(screen.getByText("≥ 1 commits in the last 24 h")).toHaveClass("text-notice-text");
  });
});
