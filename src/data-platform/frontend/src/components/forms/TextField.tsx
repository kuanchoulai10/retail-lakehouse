import { TextField as DesignSystemTextField } from "@retail-lakehouse/design-system";

interface Props {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  hint?: string;
  type?: "text" | "password";
  mono?: boolean;
}

export function TextField({ label, value, onChange, placeholder, hint, type = "text", mono }: Props) {
  return (
    <DesignSystemTextField
      label={label}
      description={hint}
      type={type}
      autoComplete="off"
      className={mono === true ? "font-mono" : undefined}
      placeholder={placeholder}
      value={value}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}
