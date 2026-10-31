import { Panel } from "@/components/Panel";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
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
  const enabledId = `${operation}-enabled`;

  return (
    <Panel title={operation}>
      <fieldset aria-label={operation} className="m-0 flex min-w-0 flex-col gap-4 border-0 p-4">
        <div className="flex items-center gap-2">
          <Switch
            id={enabledId}
            checked={values.enabled === true}
            onCheckedChange={(checked) => set("enabled", checked)}
          />
          <Label htmlFor={enabledId}>enabled</Label>
        </div>
        {fields.map(({ key, kind }) => {
          const id = `${operation}-${key}`;
          return (
            <div key={key} className="flex flex-col gap-1.5">
              <Label htmlFor={id} className="font-mono text-[13px]">
                {key}
              </Label>
              {kind === "scope" ? (
                <Select value={String(values[key] ?? "table")} onValueChange={(v) => set(key, v)}>
                  <SelectTrigger id={id} className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="table">table</SelectItem>
                    <SelectItem value="partition">partition</SelectItem>
                  </SelectContent>
                </Select>
              ) : (
                <Input
                  id={id}
                  type="number"
                  className="tabular-nums"
                  value={values[key] == null ? "" : String(values[key])}
                  onChange={(e) => set(key, numberOrNull(e.target.value))}
                />
              )}
            </div>
          );
        })}
      </fieldset>
    </Panel>
  );
}
