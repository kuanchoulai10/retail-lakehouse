import { Trash2 } from "lucide-react";
import { useState, type ReactNode } from "react";
import { ConfirmDeleteDialog } from "@/components/ConfirmDeleteDialog";
import { Panel } from "@/components/Panel";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export interface ResourceColumn<Row> {
  header: string;
  cell: (row: Row) => ReactNode;
}

export interface ResourceSectionProps<Row> {
  title: string;
  columns: ResourceColumn<Row>[];
  rows: Row[];
  rowKey: (row: Row) => string;
  emptyText?: string;
  newLabel: string;
  renderForm: (controls: { onClose: () => void }) => ReactNode;
  // A string when every row is the same kind of object; a function for a mixed list.
  objectKind: string | ((row: Row) => string);
  objectName: (row: Row) => string;
  fullPath: (row: Row) => string;
  onDelete: (row: Row) => Promise<void>;
}

// One list of child objects: a table of rows, a New button, and a typed-name delete per row.
// It owns the delete dialog's pending and error state: a resolved onDelete closes the
// dialog, a rejected one keeps it open with the error.
export function ResourceSection<Row>({
  title,
  columns,
  rows,
  rowKey,
  emptyText = "None yet.",
  newLabel,
  renderForm,
  objectKind,
  objectName,
  fullPath,
  onDelete,
}: ResourceSectionProps<Row>) {
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<Row | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);

  function openDelete(row: Row) {
    setError(null);
    setDeleting(row);
  }

  async function confirmDelete(row: Row) {
    setPending(true);
    setError(null);
    try {
      await onDelete(row);
      setDeleting(null);
    } catch (failure) {
      setError(failure);
    } finally {
      setPending(false);
    }
  }

  const kindOf = (row: Row) => (typeof objectKind === "string" ? objectKind : objectKind(row));

  return (
    <>
      <Panel
        title={title}
        actions={
          <Button type="button" size="sm" onClick={() => setCreating(true)}>
            {newLabel}
          </Button>
        }
      >
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((column) => (
                <TableHead key={column.header}>{column.header}</TableHead>
              ))}
              <TableHead className="w-10">
                <span className="sr-only">Actions</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={rowKey(row)}>
                {columns.map((column) => (
                  <TableCell key={column.header}>{column.cell(row)}</TableCell>
                ))}
                <TableCell>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    aria-label={`Delete ${objectName(row)}`}
                    onClick={() => openDelete(row)}
                  >
                    <Trash2 aria-hidden="true" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={columns.length + 1} className="text-center text-muted-foreground">
                  {emptyText}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Panel>
      {creating && renderForm({ onClose: () => setCreating(false) })}
      {deleting !== null && (
        <ConfirmDeleteDialog
          open
          onOpenChange={(next) => !next && setDeleting(null)}
          objectKind={kindOf(deleting)}
          objectName={objectName(deleting)}
          fullPath={fullPath(deleting)}
          isPending={pending}
          error={error}
          onConfirm={() => void confirmDelete(deleting)}
        />
      )}
    </>
  );
}
