import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { apiSend } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { errorMessage } from "@/format";

export const ALL_OPERATIONS = [
  "rewrite_data_files",
  "rewrite_manifests",
  "expire_snapshots",
  "remove_orphan_files",
];

interface Props {
  tableUuid: string;
  initialOperations?: string[];
  onClose: () => void;
}

export function RunMaintenanceDialog({
  tableUuid,
  initialOperations = ALL_OPERATIONS,
  onClose,
}: Props) {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<string[]>(initialOperations);
  const run = useMutation({
    mutationFn: () =>
      apiSend("POST", `/v1/tables/${tableUuid}/maintenance`, {
        operations: ALL_OPERATIONS.filter((op) => selected.includes(op)),
      }),
    onSuccess: async () => {
      await Promise.all(
        ["runs", "health"].map((key) => queryClient.invalidateQueries({ queryKey: [key, tableUuid] })),
      );
      onClose();
    },
  });

  function toggle(operation: string) {
    setSelected((current) =>
      current.includes(operation) ? current.filter((o) => o !== operation) : [...current, operation],
    );
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Run maintenance</DialogTitle>
          <DialogDescription>Runs on the whole table, ignoring thresholds</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-3">
          {ALL_OPERATIONS.map((operation) => (
            <div key={operation} className="flex items-center gap-2">
              <Checkbox
                id={`operation-${operation}`}
                checked={selected.includes(operation)}
                onCheckedChange={() => toggle(operation)}
              />
              <Label htmlFor={`operation-${operation}`} className="font-mono text-[13px]">
                {operation}
              </Label>
            </div>
          ))}
        </div>
        {run.isError && (
          <p role="alert" className="text-sm text-destructive">
            Could not start maintenance: {errorMessage(run.error)}
          </p>
        )}
        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="button"
            disabled={selected.length === 0 || run.isPending}
            onClick={() => run.mutate()}
          >
            Run
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
