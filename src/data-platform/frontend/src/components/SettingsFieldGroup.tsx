import { Select, Switch, TextField } from "@retail-lakehouse/design-system";
import { Panel } from "@retail-lakehouse/design-system";
import type { JsonObject } from "../api/types";

export interface SettingsField {
  key: string;
  kind: "number" | "nullable-number" | "scope";
}

interface Props {
  operation: string;
  fields: SettingsField[];
  values: JsonObject;
  onChange: (values: JsonObject) => void;
}

const SCOPE_ITEMS = [
  { value: "table", label: "table" },
  { value: "partition", label: "partition" },
];

function numberOrNull(raw: string): number | null {
  const parsed = Number(raw);
  return raw.trim() === "" || Number.isNaN(parsed) ? null : parsed;
}

export function SettingsFieldGroup({ operation, fields, values, onChange }: Props) {
  function set(key: string, value: unknown) {
    onChange({ ...values, [key]: value });
  }

  return (
    <Panel title={operation}>
      <fieldset aria-label={operation} className="m-0 flex min-w-0 flex-col gap-4 border-0 p-0">
        <Switch
          id={`${operation}-enabled`}
          label="enabled"
          checked={values.enabled === true}
          onCheckedChange={(checked) => set("enabled", checked)}
        />
        {fields.map(({ key, kind }) => {
          const id = `${operation}-${key}`;
          return kind === "scope" ? (
            <Select
              key={key}
              id={id}
              label={<span className="font-mono">{key}</span>}
              items={SCOPE_ITEMS}
              value={String(values[key] ?? "table")}
              onValueChange={(v) => set(key, v)}
            />
          ) : (
            <TextField
              key={key}
              id={id}
              label={<span className="font-mono">{key}</span>}
              type="number"
              className="tabular-nums"
              value={values[key] == null ? "" : String(values[key])}
              onChange={(e) => set(key, numberOrNull(e.target.value))}
            />
          );
        })}
      </fieldset>
    </Panel>
  );
}
