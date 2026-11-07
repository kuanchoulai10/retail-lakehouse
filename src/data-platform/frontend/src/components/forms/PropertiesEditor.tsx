import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { PropertyRow } from "./propertyRows";

interface Props {
  rows: PropertyRow[];
  onChange: (rows: PropertyRow[]) => void;
}

export function PropertiesEditor({ rows, onChange }: Props) {
  function update(index: number, change: Partial<PropertyRow>) {
    onChange(rows.map((row, i) => (i === index ? { ...row, ...change } : row)));
  }
  return (
    <fieldset className="m-0 flex min-w-0 flex-col gap-2 border-0 p-0">
      <div className="flex items-center justify-between">
        <legend className="text-sm font-medium">Properties</legend>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => onChange([...rows, { key: "", value: "" }])}
        >
          Add property
        </Button>
      </div>
      {rows.length === 0 && <p className="text-xs text-muted-foreground">No properties.</p>}
      {rows.map((row, index) => {
        const name = row.key === "" ? `property ${index + 1}` : row.key;
        return (
          <div key={index} className="flex items-center gap-2">
            <Input
              aria-label={`Key of ${name}`}
              placeholder="Key"
              className="font-mono text-[13px]"
              value={row.key}
              onChange={(event) => update(index, { key: event.target.value })}
            />
            <Input
              aria-label={`Value of ${name}`}
              placeholder="Value"
              className="font-mono text-[13px]"
              value={row.value}
              onChange={(event) => update(index, { value: event.target.value })}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              aria-label={`Remove ${name}`}
              onClick={() => onChange(rows.filter((_, i) => i !== index))}
            >
              <X aria-hidden="true" />
            </Button>
          </div>
        );
      })}
    </fieldset>
  );
}
