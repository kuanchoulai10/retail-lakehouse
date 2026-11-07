import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Panel } from "@/components/Panel";
import { Alert } from "@/components/ui/alert";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiGet, apiSend } from "../api/client";
import { invalidateTableState } from "../api/invalidateTableState";
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
  const resetRef = useRef<HTMLButtonElement>(null);

  const save = useMutation({
    mutationFn: (settings: JsonObject) =>
      apiSend("PUT", `/v1/tables/${table.uuid}/settings`, settings),
    onSuccess: () => invalidateTableState(queryClient, table.uuid),
  });
  const reset = useMutation({
    mutationFn: async (presetId: string) => {
      const preset = await apiGet<TableMaintenancePresetApiResponse>(
        `/v1/table-maintenance-presets/${presetId}`,
      );
      await apiSend("PUT", `/v1/tables/${table.uuid}/settings`, preset.settings);
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
        <Alert role="status">This table has no maintenance settings yet.</Alert>
      )}
      <Panel title="Reconciliation">
        <div className="flex flex-col gap-1.5 p-4">
          <Label htmlFor="reconcile_interval_seconds" className="font-mono text-[13px]">
            reconcile_interval_seconds
          </Label>
          <Input
            id="reconcile_interval_seconds"
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
      {error && <Alert variant="destructive">Could not save settings: {errorMessage(error)}</Alert>}
      <div className="sticky bottom-0 flex justify-end gap-2 border-t border-border bg-background py-3">
        {table.source_preset_id !== null && (
          <Button ref={resetRef} type="button" variant="outline" onClick={() => setConfirming(true)}>
            Reset to preset
          </Button>
        )}
        <Button type="submit" disabled={busy}>
          Save
        </Button>
      </div>
      <AlertDialog open={confirming} onOpenChange={setConfirming}>
        <AlertDialogContent
          onCloseAutoFocus={(event) => {
            event.preventDefault();
            resetRef.current?.focus();
          }}
        >
          <AlertDialogHeader>
            <AlertDialogTitle>Reset to preset</AlertDialogTitle>
            <AlertDialogDescription>
              Replace these settings with the preset's? Unsaved edits are discarded.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep editing</AlertDialogCancel>
            <AlertDialogAction
              disabled={busy}
              onClick={() => {
                save.reset();
                reset.mutate(table.source_preset_id as string);
              }}
            >
              Confirm reset
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </form>
  );
}
