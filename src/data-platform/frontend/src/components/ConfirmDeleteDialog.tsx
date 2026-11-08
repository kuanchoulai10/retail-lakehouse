import {
  AlertDialog,
  AlertDialogCancel,
  Banner,
  Button,
  TextField,
} from "@retail-lakehouse/design-system";
import { useState } from "react";
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

export function ConfirmDeleteDialog({
  open,
  onOpenChange,
  objectKind,
  objectName,
  fullPath,
  onConfirm,
  isPending,
  error,
}: Props) {
  const [typed, setTyped] = useState("");
  const [wasOpen, setWasOpen] = useState(open);
  if (open !== wasOpen) {
    setWasOpen(open);
    if (!open) setTyped("");
  }
  const hasError = error !== null && error !== undefined;
  return (
    <AlertDialog
      isOpen={open}
      onOpenChange={onOpenChange}
      title={`Delete ${objectKind}`}
      description={
        <>
          This deletes <span className="font-mono">{fullPath}</span> from the catalog. It cannot be
          undone.
        </>
      }
      footer={
        <>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <Button type="button" disabled={typed !== objectName || isPending} onClick={onConfirm}>
            Delete
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <TextField
          label={`Type ${objectName} to confirm`}
          autoComplete="off"
          value={typed}
          onChange={(event) => setTyped(event.target.value)}
        />
        {hasError && <Banner type="negative" title={errorMessage(error)} />}
      </div>
    </AlertDialog>
  );
}
