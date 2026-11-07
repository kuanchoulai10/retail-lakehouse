import type { FormEvent, ReactNode } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface Props {
  title: string;
  description: ReactNode;
  submitLabel: string;
  isPending: boolean;
  // A validation or API message; shown above the buttons, the dialog stays open.
  error: string | null;
  // Extra controls beside the error, such as Reload after a conflict.
  errorAction?: ReactNode;
  onSubmit: () => void;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}

// The shell every create and edit dialog shares: title, fields, error, Cancel and submit.
export function FormDialog({
  title,
  description,
  submitLabel,
  isPending,
  error,
  errorAction,
  onSubmit,
  onClose,
  children,
  wide,
}: Props) {
  function submit(event: FormEvent) {
    event.preventDefault();
    onSubmit();
  }
  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent className={wide === true ? "max-h-[85vh] overflow-y-auto sm:max-w-2xl" : "max-h-[85vh] overflow-y-auto"}>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="flex flex-col gap-4">
          {children}
          {error !== null && (
            <div className="flex items-center justify-between gap-3">
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
              {errorAction}
            </div>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {submitLabel}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
