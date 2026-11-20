import { TextField } from "@retail-lakehouse/design-system";
import type { ReactNode } from "react";
import { formatBytes, formatSeconds } from "@/format";

export interface WholeNumberInput {
  label: string;
  value: string;
  onChange: (value: string) => void;
  // Shown under the label, such as what an empty optional field means; a property key in it is
  // set in mono.
  hint?: ReactNode;
  // Reads the value back in a friendlier unit under the label: 3600 seconds as "1 h".
  unit?: "seconds" | "bytes";
}

function readBack(value: string, unit: WholeNumberInput["unit"]): string | undefined {
  if (unit === undefined || !/^\d+$/.test(value.trim())) return undefined;
  const number = Number(value.trim());
  return unit === "seconds" ? formatSeconds(number) : formatBytes(number);
}

// A whole-number field kept as text (not type="number", which reports half-typed input such as
// "1e" as empty), so an empty optional value and a half-typed one survive
// until the form is submitted and checked.
export function WholeNumberField({ label, value, onChange, hint, unit }: WholeNumberInput) {
  const read = readBack(value, unit);
  const description =
    read === undefined ? hint : hint === undefined ? read : (
      <>
        {read}. {hint}
      </>
    );
  return (
    <TextField
      label={label}
      description={description}
      type="text"
      inputMode="numeric"
      className="tabular-nums"
      value={value}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}
