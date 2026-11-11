import { Badge, Button, IconButton, IconX, TextField } from "@retail-lakehouse/design-system";
import { useState, type KeyboardEvent } from "react";

interface Props {
  // The field's name, plural: "Catalogs", "Namespaces", "Tables".
  label: string;
  hint: string;
  globs: string[];
  onChange: (globs: string[]) => void;
}

// A list of globs as chips, with an input that adds one on Enter, on Add, or when focus leaves
// it, so a glob typed but not yet added is not lost when the dialog is submitted.
export function GlobListField({ label, hint, globs, onChange }: Props) {
  const [pending, setPending] = useState("");
  const noun = label.toLowerCase();

  function add() {
    const glob = pending.trim();
    setPending("");
    if (glob === "" || globs.includes(glob)) return;
    onChange([...globs, glob]);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key !== "Enter") return;
    event.preventDefault();
    add();
  }

  return (
    <fieldset className="m-0 flex min-w-0 flex-col gap-2 border-0 p-0">
      <legend className="type-label-large mb-2">{label}</legend>
      {globs.length > 0 && (
        <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
          {globs.map((glob) => (
            <li key={glob}>
              <Badge className="min-h-control gap-1 pr-0 pl-3 font-mono">
                {glob}
                <IconButton
                  styleType="ghost"
                  className="size-control"
                  aria-label={`Remove ${noun} glob ${glob}`}
                  icon={<IconX />}
                  onClick={() => onChange(globs.filter((g) => g !== glob))}
                />
              </Badge>
            </li>
          ))}
        </ul>
      )}
      <div className="flex items-end gap-2">
        <div className="min-w-0 flex-1">
          <TextField
            hideLabel
            label={`New ${noun} glob`}
            placeholder="Glob, such as orders_*"
            className="font-mono"
            autoComplete="off"
            value={pending}
            onChange={(event) => setPending(event.target.value)}
            onKeyDown={onKeyDown}
            onBlur={add}
          />
        </div>
        <Button type="button" styleType="outlined" aria-label={`Add ${noun} glob`} onClick={add}>
          Add
        </Button>
      </div>
      <p className="type-body-small text-on-surface-variant">{hint}</p>
    </fieldset>
  );
}
