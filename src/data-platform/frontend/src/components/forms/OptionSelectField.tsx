import { SelectField, type SelectOption } from "./SelectField";

// The select's own value for "Procedure default": a select item cannot carry an empty value.
const PROCEDURE_DEFAULT = "procedure-default";

export const ON_OFF: SelectOption<"true" | "false">[] = [
  { value: "true", label: "On" },
  { value: "false", label: "Off" },
];

interface Props<Value extends string> {
  label: string;
  // "" when the option is left to the procedure.
  value: Value | "";
  options: SelectOption<Value>[];
  onChange: (value: Value | "") => void;
}

// A procedure option chosen from a list, with "Procedure default" first to leave it unset.
export function OptionSelectField<Value extends string>({ label, value, options, onChange }: Props<Value>) {
  return (
    <SelectField<string>
      label={label}
      value={value === "" ? PROCEDURE_DEFAULT : value}
      options={[{ value: PROCEDURE_DEFAULT, label: "Procedure default" }, ...options]}
      onChange={(next) => onChange(next === PROCEDURE_DEFAULT ? "" : (next as Value))}
    />
  );
}
