import { useId } from "react";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

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
  const id = useId();
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Select value={value} onValueChange={(next) => onChange(next as Value)}>
        <SelectTrigger id={id} className="w-full">
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {options.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
