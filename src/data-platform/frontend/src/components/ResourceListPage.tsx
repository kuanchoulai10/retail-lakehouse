import { Trash2 } from "lucide-react";
import { useState, type ReactNode } from "react";
import { ConfirmDeleteDialog } from "@/components/ConfirmDeleteDialog";
import type { Crumb } from "@/components/Breadcrumbs";
import { PageHeader } from "@/components/PageHeader";
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

interface Props<Row> {
  title: string;
  breadcrumbs: Crumb[];
  columns: ResourceColumn<Row>[];
  rows: Row[];
  rowKey: (row: Row) => string;
  newLabel: string;
  renderForm: (controls: { onClose: () => void }) => ReactNode;
  objectKind: string;
  objectName: (row: Row) => string;
  fullPath: (row: Row) => string;
  onDelete: (row: Row) => Promise<void>;
}

export function ResourceListPage<Row>({
  title,
  breadcrumbs,
  columns,
  rows,
  rowKey,
  newLabel,
  renderForm,
  objectKind,
  objectName,
  fullPath,
  onDelete,
}: Props<Row>) {
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

  return (
    <>
      <PageHeader
        title={title}
        breadcrumbs={breadcrumbs}
        actions={
          <Button type="button" onClick={() => setCreating(true)}>
            {newLabel}
          </Button>
        }
      />
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
        </TableBody>
      </Table>
      {creating && renderForm({ onClose: () => setCreating(false) })}
      {deleting !== null && (
        <ConfirmDeleteDialog
          open
          onOpenChange={(next) => !next && setDeleting(null)}
          objectKind={objectKind}
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
