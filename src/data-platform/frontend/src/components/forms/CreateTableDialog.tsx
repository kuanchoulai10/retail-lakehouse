import { useMutation, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import { useState } from "react";
import { catalogQueryKeys } from "@/api/catalogQueryKeys";
import type { CreateTableApiRequest, SchemaFieldApiRequest } from "@/api/catalogTypes";
import { apiSend } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { errorMessage } from "@/format";
import { tablesApiPath } from "@/lib/catalogPaths";
import { FormDialog } from "./FormDialog";
import { PropertiesEditor } from "./PropertiesEditor";
import { propertiesFromRows, type PropertyRow } from "./propertyRows";
import { TextField } from "./TextField";

// The partition transforms upstream's CreateTableModal offers.
const TRANSFORMS = ["identity", "year", "month", "day", "hour", "bucket[16]", "truncate[10]"];

interface FieldRow {
  name: string;
  type: string;
  required: boolean;
  doc: string;
}

interface PartitionRow {
  sourceColumn: string;
  transform: string;
}

const EMPTY_FIELD: FieldRow = { name: "", type: "", required: true, doc: "" };

interface Props {
  catalog: string;
  namespace: string[];
  onClose: () => void;
}

function schemaField(row: FieldRow): SchemaFieldApiRequest {
  const field: SchemaFieldApiRequest = { name: row.name.trim(), type: row.type.trim(), required: row.required };
  if (row.doc.trim() !== "") field.doc = row.doc.trim();
  return field;
}

function replaceAt<T>(items: T[], index: number, change: Partial<T>): T[] {
  return items.map((item, i) => (i === index ? { ...item, ...change } : item));
}

// Column types are text: an Iceberg primitive or the API's nested syntax, such as
// list<string> or struct<city: required string>.
export function CreateTableDialog({ catalog, namespace, onClose }: Props) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [location, setLocation] = useState("");
  const [fields, setFields] = useState<FieldRow[]>([EMPTY_FIELD]);
  const [partitions, setPartitions] = useState<PartitionRow[]>([]);
  const [rows, setRows] = useState<PropertyRow[]>([]);
  const [invalid, setInvalid] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: (body: CreateTableApiRequest) => apiSend("POST", tablesApiPath(catalog, namespace), body),
    // A write can fail after part of it landed, so the page refetches either way; the dialog
    // closes only on success and otherwise shows the API's message, which says what landed.
    onSettled: async (_data, error) => {
      await queryClient.invalidateQueries({ queryKey: catalogQueryKeys.tables(catalog, namespace) });
      if (error === null) onClose();
    },
  });

  function validate(): string | null {
    if (name.trim() === "") return "Name is required";
    if (fields.length === 0) return "Add at least one field";
    if (fields.some((field) => field.name.trim() === "" || field.type.trim() === "")) {
      return "Every field needs a name and a type";
    }
    if (partitions.some((partition) => partition.sourceColumn.trim() === "")) {
      return "Every partition needs a column";
    }
    return null;
  }

  function submit() {
    const problem = validate();
    setInvalid(problem);
    if (problem !== null) return;
    const body: CreateTableApiRequest = {
      name: name.trim(),
      schema_fields: fields.map(schemaField),
      partition_fields: partitions.map((p) => ({ source_column: p.sourceColumn.trim(), transform: p.transform })),
      properties: propertiesFromRows(rows),
    };
    if (location.trim() !== "") body.location = location.trim();
    create.mutate(body);
  }

  return (
    <FormDialog
      title="New table"
      description={
        <>
          Creates an Iceberg table in{" "}
          <span className="font-mono text-[13px]">{[catalog, ...namespace].join(" / ")}</span>.
        </>
      }
      submitLabel="Create"
      isPending={create.isPending}
      error={invalid ?? (create.isError ? errorMessage(create.error) : null)}
      onSubmit={submit}
      onClose={onClose}
      wide
    >
      <TextField label="Name" mono placeholder="my_table" value={name} onChange={setName} />
      <TextField
        label="Location (optional)"
        mono
        placeholder="s3://bucket/path/to/table"
        hint="Must be within the catalog's allowed locations."
        value={location}
        onChange={setLocation}
      />
      <fieldset className="m-0 flex min-w-0 flex-col gap-2 border-0 p-0">
        <div className="flex items-center justify-between">
          <legend className="text-sm font-medium">Schema</legend>
          <Button type="button" variant="outline" size="sm" onClick={() => setFields([...fields, EMPTY_FIELD])}>
            Add field
          </Button>
        </div>
        {fields.map((field, index) => {
          const label = `Field ${index + 1}`;
          return (
            <div key={index} className="flex items-center gap-2">
              <Input
                aria-label={`${label} name`}
                placeholder="Name"
                className="font-mono text-[13px]"
                value={field.name}
                onChange={(e) => setFields(replaceAt(fields, index, { name: e.target.value }))}
              />
              <Input
                aria-label={`${label} type`}
                placeholder="long, string, list<string>"
                className="font-mono text-[13px]"
                value={field.type}
                onChange={(e) => setFields(replaceAt(fields, index, { type: e.target.value }))}
              />
              <Input
                aria-label={`${label} doc`}
                placeholder="Doc (optional)"
                value={field.doc}
                onChange={(e) => setFields(replaceAt(fields, index, { doc: e.target.value }))}
              />
              <label className="flex shrink-0 items-center gap-1.5 text-sm">
                <Checkbox
                  aria-label={`${label} required`}
                  checked={field.required}
                  onCheckedChange={(next) => setFields(replaceAt(fields, index, { required: next === true }))}
                />
                Required
              </label>
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                aria-label={`Remove ${label.toLowerCase()}`}
                onClick={() => setFields(fields.filter((_, i) => i !== index))}
              >
                <X aria-hidden="true" />
              </Button>
            </div>
          );
        })}
      </fieldset>
      <fieldset className="m-0 flex min-w-0 flex-col gap-2 border-0 p-0">
        <div className="flex items-center justify-between">
          <legend className="text-sm font-medium">Partition spec</legend>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setPartitions([...partitions, { sourceColumn: "", transform: "identity" }])}
          >
            Add partition
          </Button>
        </div>
        {partitions.length === 0 && (
          <p className="text-xs text-muted-foreground">No partitions. The table is unpartitioned.</p>
        )}
        {partitions.map((partition, index) => {
          const label = `Partition ${index + 1}`;
          return (
            <div key={index} className="flex items-center gap-2">
              <Input
                aria-label={`${label} column`}
                placeholder="Column"
                className="font-mono text-[13px]"
                value={partition.sourceColumn}
                onChange={(e) => setPartitions(replaceAt(partitions, index, { sourceColumn: e.target.value }))}
              />
              <Select
                value={partition.transform}
                onValueChange={(transform) => setPartitions(replaceAt(partitions, index, { transform }))}
              >
                <SelectTrigger aria-label={`${label} transform`} className="w-40 font-mono text-[13px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TRANSFORMS.map((transform) => (
                    <SelectItem key={transform} value={transform} className="font-mono text-[13px]">
                      {transform}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                aria-label={`Remove ${label.toLowerCase()}`}
                onClick={() => setPartitions(partitions.filter((_, i) => i !== index))}
              >
                <X aria-hidden="true" />
              </Button>
            </div>
          );
        })}
      </fieldset>
      <PropertiesEditor rows={rows} onChange={setRows} />
    </FormDialog>
  );
}
