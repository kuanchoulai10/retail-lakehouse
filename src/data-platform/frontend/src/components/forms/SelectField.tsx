import { Select } from "@retail-lakehouse/design-system";

export interface SelectOption<Value extends string> {
  value: Value;
  label: string;
}

interface Props<Value extends string> {
  label: string;
  value: Value | undefined;
  options: SelectOption<Value>[];
  onChange: (value: Value) => void;
  placeholder?: string;
}

export function SelectField<Value extends string>({
  label,
  value,
  options,
  onChange,
  placeholder,
}: Props<Value>) {
  return (
    <Select
      label={label}
      value={value}
      items={options}
      placeholder={placeholder}
      onValueChange={(next) => onChange(next as Value)}
    />
  );
}
