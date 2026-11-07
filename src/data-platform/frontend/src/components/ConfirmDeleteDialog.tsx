import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { errorMessage } from "@/format";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  objectKind: string;
  objectName: string;
  fullPath: string;
  onConfirm: () => void;
  isPending: boolean;
  error: unknown;
}

function DeleteForm({
  objectKind,
  objectName,
  fullPath,
  onConfirm,
  isPending,
  error,
  onCancel,
}: Omit<Props, "open" | "onOpenChange"> & { onCancel: () => void }) {
  const [typed, setTyped] = useState("");
  const hasError = error !== null && error !== undefined;
  return (
    <>
      <DialogHeader>
        <DialogTitle>Delete {objectKind}</DialogTitle>
        <DialogDescription>
          This deletes <span className="font-mono text-[13px] text-foreground">{fullPath}</span>{" "}
          from the catalog. It cannot be undone.
        </DialogDescription>
      </DialogHeader>
      <div className="flex flex-col gap-2">
        <Label htmlFor="confirm-delete-name">
          Type <span className="font-mono text-[13px]">{objectName}</span> to confirm
        </Label>
        <Input
          id="confirm-delete-name"
          autoComplete="off"
          value={typed}
          onChange={(event) => setTyped(event.target.value)}
        />
      </div>
      {hasError && (
        <p role="alert" className="text-sm text-destructive">
          {errorMessage(error)}
        </p>
      )}
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button
          type="button"
          variant="destructive"
          disabled={typed !== objectName || isPending}
          onClick={onConfirm}
        >
          Delete
        </Button>
      </DialogFooter>
    </>
  );
}

export function ConfirmDeleteDialog({ open, onOpenChange, ...rest }: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DeleteForm {...rest} onCancel={() => onOpenChange(false)} />
      </DialogContent>
    </Dialog>
  );
}
