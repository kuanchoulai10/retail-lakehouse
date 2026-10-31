import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { TableStorageApiResponse } from "../api/types";
import { StoragePanel } from "./StoragePanel";

function storage(overrides: Partial<TableStorageApiResponse> = {}): TableStorageApiResponse {
  return {
    current_bytes: 335544320,
    current_files: 100,
    old_snapshot_bytes: 5242880,
    old_snapshot_files: 12,
    window_days: 30,
    reclaimed: { rewritten_bytes_count: 1048576, deleted_manifest_lists_count: 7 },
    attempts_without_metrics: 0,
    ...overrides,
  };
}

describe("StoragePanel", () => {
  it("shows the bytes held only by old snapshots", () => {
    render(<StoragePanel storage={storage()} />);
    expect(screen.getByText("5.0 MB")).toBeInTheDocument();
    expect(screen.getByText("320.0 MB")).toBeInTheDocument();
  });

  it("shows what maintenance reclaimed in the window", () => {
    render(<StoragePanel storage={storage()} />);
    expect(screen.getByText("Reclaimed in the last 30 days")).toBeInTheDocument();
    expect(screen.getByText("1.0 MB")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
  });

  it("notes attempts that reported no metrics", () => {
    render(<StoragePanel storage={storage({ attempts_without_metrics: 2 })} />);
    expect(screen.getByText(/2 attempts in this window reported no metrics/)).toBeInTheDocument();
  });

  it("shows no note when every attempt reported metrics", () => {
    render(<StoragePanel storage={storage()} />);
    expect(screen.queryByText(/reported no metrics/)).not.toBeInTheDocument();
  });
});
