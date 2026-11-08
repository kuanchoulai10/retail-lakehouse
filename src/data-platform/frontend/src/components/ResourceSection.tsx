import {
  Banner,
  Button,
  createDataTableColumnHelper,
  DataTable,
  IconButton,
  Panel,
  SerendieSymbolTrash,
} from "@retail-lakehouse/design-system";
import { useState, type ReactNode } from "react";
import type { RowData } from "@tanstack/react-table";
import { ConfirmDeleteDialog } from "@/components/ConfirmDeleteDialog";

export interface ResourceColumn<Row> {
  header: string;
  cell: (row: Row) => ReactNode;
}

export interface ResourceSectionProps<Row extends RowData> {
  title: string;
  columns: ResourceColumn<Row>[];
  rows: Row[];
  rowKey: (row: Row) => string;
  emptyText?: string;
  // Messages for parts of the list that could not be loaded; the rows that did load still show.
  errors?: string[];
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
export function ResourceSection<Row extends RowData>({
  title,
  columns,
  rows,
  rowKey,
  emptyText = "None yet.",
  errors = [],
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

  const column = createDataTableColumnHelper<Row>();
  const tableColumns = column.columns([
    ...columns.map((spec) =>
      column.display({ id: spec.header, header: spec.header, cell: (info) => spec.cell(info.row.original) }),
    ),
    column.display({
      id: "actions",
      header: () => <span className="sr-only">Actions</span>,
      cell: (info) => (
        <div className="flex justify-end">
          <IconButton
            styleType="ghost"
            shape="rectangle"
            aria-label={`Delete ${objectName(info.row.original)}`}
            icon={<SerendieSymbolTrash />}
            onClick={() => openDelete(info.row.original)}
          />
        </div>
      ),
    }),
  ]);

  return (
    <>
      <Panel
        title={title}
        actions={
          <Button type="button" size="small" onClick={() => setCreating(true)}>
            {newLabel}
          </Button>
        }
      >
        {errors.length > 0 && (
          <Banner
            type="negative"
            title={errors.length === 1 ? errors[0] : "Parts of this list could not be loaded"}
            className="mb-3"
          >
            {errors.length > 1 && errors.map((message) => <p key={message}>{message}</p>)}
          </Banner>
        )}
        <DataTable
          caption={`${title} list`}
          columns={tableColumns}
          data={rows}
          getRowId={(row) => rowKey(row)}
          emptyState={emptyText}
        />
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
