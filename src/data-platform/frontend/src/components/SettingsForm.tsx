import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  Banner,
  Button,
  Switch,
  TextField,
} from "@retail-lakehouse/design-system";
import { useState } from "react";
import { Panel } from "@retail-lakehouse/design-system";
import type { TableApiResponse } from "@/api/generated/model";
import { getTableMaintenancePreset } from "@/api/generated/table-maintenance-presets/table-maintenance-presets";
import { updateTableSettings } from "@/api/generated/tables/tables";
import { invalidateTableState } from "@/api/invalidateTableState";
import type { JsonObject } from "@/lib/jsonObject";
import { errorMessage } from "../format";
import { SettingsFieldGroup, type SettingsField } from "./SettingsFieldGroup";

const DRY_RUN_DESCRIPTION =
  "Reconcile and record as usual, but start no maintenance. Run maintenance still runs.";

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
    mutationFn: (settings: JsonObject) => updateTableSettings(table.uuid, settings),
    onSuccess: () => invalidateTableState(queryClient, table.uuid),
  });
  const reset = useMutation({
    mutationFn: async (presetId: string) => {
      const preset = await getTableMaintenancePreset(presetId);
      await updateTableSettings(table.uuid, preset.settings);
    },
    onSuccess: () => invalidateTableState(queryClient, table.uuid),
  });

  const error = save.isError ? save.error : reset.isError ? reset.error : null;
  const busy = save.isPending || reset.isPending;

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        reset.reset();
        save.mutate(draft);
      }}
    >
      {table.settings === null && (
        <Banner type="information" title="This table has no maintenance settings yet." />
      )}
      <Panel title="Reconciliation">
        <div className="mb-4">
          <Switch
            id="dry_run"
            label="Dry run"
            aria-describedby="dry_run-description"
            checked={draft.dry_run === true}
            onCheckedChange={(checked) => setDraft({ ...draft, dry_run: checked })}
          />
          <p id="dry_run-description" className="type-body-small text-on-surface-variant">
            {DRY_RUN_DESCRIPTION}
          </p>
        </div>
        <div>
          <TextField
            id="reconcile_interval_seconds"
            label={<span className="font-mono">reconcile_interval_seconds</span>}
            type="number"
            className="tabular-nums"
            value={
              draft.reconcile_interval_seconds == null ? "" : String(draft.reconcile_interval_seconds)
            }
            onChange={(e) =>
              setDraft({
                ...draft,
                reconcile_interval_seconds: e.target.value === "" ? null : Number(e.target.value),
              })
            }
          />
        </div>
      </Panel>
      {OPERATIONS.map(({ operation, fields }) => (
        <SettingsFieldGroup
          key={operation}
          operation={operation}
          fields={fields}
          values={sectionOf(draft, operation)}
          onChange={(values) => setDraft({ ...draft, [operation]: values })}
        />
      ))}
      {error && <Banner type="negative" title={`Could not save settings: ${errorMessage(error)}`} />}
      <div className="sticky bottom-0 flex justify-end gap-2 border-t border-outline-dim bg-surface py-3">
        {table.source_preset_id !== null && (
          <Button type="button" styleType="outlined" onClick={() => setConfirming(true)}>
            Reset to preset
          </Button>
        )}
        <Button type="submit" disabled={busy}>
          Save
        </Button>
      </div>
      <AlertDialog
        isOpen={confirming}
        onOpenChange={setConfirming}
        title="Reset to preset"
        description="Replace these settings with the preset's? Unsaved edits are discarded."
        footer={
          <>
            <AlertDialogCancel>Keep editing</AlertDialogCancel>
            <AlertDialogAction
              styleType="negative"
              disabled={busy}
              onClick={() => {
                save.reset();
                reset.mutate(table.source_preset_id as string);
              }}
            >
              Confirm reset
            </AlertDialogAction>
          </>
        }
      />
    </form>
  );
}
