import { CheckBox } from "@retail-lakehouse/design-system";

interface Props {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

export function CheckboxField({ label, checked, onChange }: Props) {
  return <CheckBox label={label} checked={checked} onCheckedChange={(next) => onChange(next === true)} />;
}
