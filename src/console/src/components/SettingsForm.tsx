import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { apiGet, apiSend } from "../api/client";
import type { JsonObject, TableApiResponse, TableMaintenancePresetApiResponse } from "../api/types";
import { errorMessage } from "../format";
import { SettingsFieldGroup, type SettingsField } from "./SettingsFieldGroup";

const INTERVAL: SettingsField = { key: "min_interval_seconds", kind: "number" };

const OPERATIONS: { operation: string; fields: SettingsField[] }[] = [
  {
    operation: "rewrite_data_files",
    fields: [
      INTERVAL,
      { key: "scope", kind: "scope" },
      { key: "target_file_size_bytes", kind: "nullable-number" },
      { key: "min_reducible_files", kind: "number" },
    ],
  },
  {
    operation: "rewrite_manifests",
    fields: [
      INTERVAL,
      { key: "min_small_manifests", kind: "number" },
      { key: "small_manifest_bytes", kind: "nullable-number" },
    ],
  },
  {
    operation: "expire_snapshots",
    fields: [
      INTERVAL,
      { key: "older_than_seconds", kind: "number" },
      { key: "retain_last", kind: "number" },
    ],
  },
  {
    operation: "remove_orphan_files",
    fields: [INTERVAL, { key: "older_than_seconds", kind: "number" }],
  },
];

function sectionOf(settings: JsonObject, operation: string): JsonObject {
  const section = settings[operation];
  return section && typeof section === "object" ? (section as JsonObject) : {};
}

interface Props {
  table: TableApiResponse;
}

export function SettingsForm({ table }: Props) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<JsonObject>(table.settings ?? {});
  const [confirming, setConfirming] = useState(false);

  const save = useMutation({
    mutationFn: (settings: JsonObject) =>
      apiSend("PUT", `/v1/tables/${table.uuid}/settings`, settings),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["table", table.uuid] }),
  });
  const reset = useMutation({
    mutationFn: async (presetId: string) => {
      const preset = await apiGet<TableMaintenancePresetApiResponse>(
        `/v1/table-maintenance-presets/${presetId}`,
      );
      await apiSend("PUT", `/v1/tables/${table.uuid}/settings`, preset.settings);
    },
    onSuccess: () => {
      setConfirming(false);
      return queryClient.invalidateQueries({ queryKey: ["table", table.uuid] });
    },
  });

  const error = save.isError ? save.error : reset.isError ? reset.error : null;
  const busy = save.isPending || reset.isPending;

  return (
    <form
      className="settings"
      onSubmit={(event) => {
        event.preventDefault();
        reset.reset();
        save.mutate(draft);
      }}
    >
      {table.settings === null && (
        <p role="status" className="notice">
          This table has no maintenance settings yet.
        </p>
      )}
      <label className="field">
        reconcile_interval_seconds
        <input
          type="number"
          value={draft.reconcile_interval_seconds == null ? "" : String(draft.reconcile_interval_seconds)}
          onChange={(e) =>
            setDraft({
              ...draft,
              reconcile_interval_seconds: e.target.value === "" ? null : Number(e.target.value),
            })
          }
        />
      </label>
      {OPERATIONS.map(({ operation, fields }) => (
        <SettingsFieldGroup
          key={operation}
          operation={operation}
          fields={fields}
          values={sectionOf(draft, operation)}
          onChange={(values) => setDraft({ ...draft, [operation]: values })}
        />
      ))}
      {error && (
        <p role="alert" className="error">
          Could not save settings: {errorMessage(error)}
        </p>
      )}
      <div className="actions">
        {table.source_preset_id !== null &&
          (confirming ? (
            <span role="group" aria-label="Confirm reset">
              Replace these settings with the preset's?
              <button type="button" onClick={() => setConfirming(false)}>
                Keep editing
              </button>
              <button
                type="button"
                className="primary"
                disabled={busy}
                onClick={() => {
                  save.reset();
                  reset.mutate(table.source_preset_id as string);
                }}
              >
                Confirm reset
              </button>
            </span>
          ) : (
            <button type="button" onClick={() => setConfirming(true)}>
              Reset to preset
            </button>
          ))}
        <button type="submit" className="primary" disabled={busy}>
          Save
        </button>
      </div>
    </form>
  );
}
