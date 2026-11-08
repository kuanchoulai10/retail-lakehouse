import { useId, type FormEvent, type ReactNode } from "react";
import { Banner, Button, ModalDialog } from "@retail-lakehouse/design-system";

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
}

// The shell every create and edit dialog shares: title, fields, error, Cancel and submit.
// The fields stack in one column at every width; the dialog itself is a full-screen sheet on phones.
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
}: Props) {
  const formId = useId();
  function submit(event: FormEvent) {
    event.preventDefault();
    onSubmit();
  }
  return (
    <ModalDialog
      isOpen
      onOpenChange={(next) => !next && onClose()}
      title={title}
      description={description}
      footer={
        <>
          <Button type="button" styleType="outlined" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form={formId} disabled={isPending}>
            {submitLabel}
          </Button>
        </>
      }
    >
      <form id={formId} aria-label={title} onSubmit={submit} className="grid grid-cols-1 gap-4">
        {children}
        {error !== null && (
          <div className="flex items-center justify-between gap-3">
            <Banner type="negative" title={error} className="flex-1" />
            {errorAction}
          </div>
        )}
      </form>
    </ModalDialog>
  );
}
