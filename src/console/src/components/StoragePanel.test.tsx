import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { TableStorageApiResponse, TableStorageReclaimedApiResponse } from "../api/types";
import { StoragePanel } from "./StoragePanel";

function reclaimed(
  overrides: Partial<TableStorageReclaimedApiResponse> = {},
): TableStorageReclaimedApiResponse {
  return {
    rewritten_data_files: 0,
    added_data_files: 0,
    rewritten_bytes: 0,
    rewritten_manifests: 0,
    added_manifests: 0,
    expired_snapshots: 0,
    deleted_data_files: 0,
    deleted_manifest_files: 0,
    deleted_position_delete_files: 0,
    deleted_equality_delete_files: 0,
    ...overrides,
  };
}

function storage(overrides: Partial<TableStorageApiResponse> = {}): TableStorageApiResponse {
  return {
    current_bytes: 335544320,
    current_files: 100,
    old_snapshot_bytes: 5242880,
    old_snapshot_files: 12,
    window_days: 30,
    reclaimed: reclaimed({ rewritten_bytes: 1048576, expired_snapshots: 7 }),
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

  it("shows rewritten data files with what they were rewritten into", () => {
    render(
      <StoragePanel
        storage={storage({ reclaimed: reclaimed({ rewritten_data_files: 12, added_data_files: 3 }) })}
      />,
    );
    expect(screen.getByText("Data files rewritten")).toBeInTheDocument();
    expect(screen.getByText("12 → 3")).toBeInTheDocument();
  });

  it("sums the files snapshot expiry deleted", () => {
    render(
      <StoragePanel
        storage={storage({
          reclaimed: reclaimed({ deleted_data_files: 4, deleted_manifest_files: 5 }),
        })}
      />,
    );
    expect(screen.getByText("Files deleted by expiry")).toBeInTheDocument();
    expect(screen.getByText("9")).toBeInTheDocument();
  });

  it("says nothing was reclaimed only when every value is zero", () => {
    render(<StoragePanel storage={storage({ reclaimed: reclaimed() })} />);
    expect(screen.getByText("Nothing reclaimed.")).toBeInTheDocument();
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
