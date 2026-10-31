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

function numberOrNull(raw: string): number | null {
  const parsed = Number(raw);
  return raw.trim() === "" || Number.isNaN(parsed) ? null : parsed;
}

export function SettingsFieldGroup({ operation, fields, values, onChange }: Props) {
  function set(key: string, value: unknown) {
    onChange({ ...values, [key]: value });
  }

  return (
    <fieldset aria-label={operation} className="settings-group">
      <legend>{operation}</legend>
      <label className="check">
        <input
          type="checkbox"
          checked={values.enabled === true}
          onChange={(event) => set("enabled", event.target.checked)}
        />
        enabled
      </label>
      {fields.map(({ key, kind }) => (
        <label key={key} className="field">
          {key}
          {kind === "scope" ? (
            <select value={String(values[key] ?? "table")} onChange={(e) => set(key, e.target.value)}>
              <option value="table">table</option>
              <option value="partition">partition</option>
            </select>
          ) : (
            <input
              type="number"
              value={values[key] == null ? "" : String(values[key])}
              onChange={(e) => set(key, numberOrNull(e.target.value))}
            />
          )}
        </label>
      ))}
    </fieldset>
  );
}
