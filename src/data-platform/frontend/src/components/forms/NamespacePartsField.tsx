import {
  Button,
  IconButton,
  IconX,
  TextField,
} from "@retail-lakehouse/design-system";

interface Props {
  parts: string[];
  onChange: (parts: string[]) => void;
}

// One input per namespace level, so a dot stays part of a level's name ("a.b" is one level).
export function NamespacePartsField({ parts, onChange }: Props) {
  return (
    <fieldset className="m-0 flex min-w-0 flex-col gap-2 border-0 p-0">
      <div className="flex items-center justify-between">
        <legend className="type-label-large">Namespace</legend>
        <Button type="button" styleType="outlined" size="small" onClick={() => onChange([...parts, ""])}>
          Add level
        </Button>
      </div>
      {parts.map((part, index) => (
        <div key={index} className="flex items-center gap-2">
          <div className="min-w-0 flex-1">
            <TextField
              hideLabel
              label={`Namespace level ${index + 1}`}
              className="font-mono"
              autoComplete="off"
              value={part}
              onChange={(event) => onChange(parts.map((p, i) => (i === index ? event.target.value : p)))}
            />
          </div>
          <IconButton
            styleType="ghost"
            aria-label={`Remove level ${index + 1}`}
            icon={<IconX />}
            disabled={parts.length === 1}
            onClick={() => onChange(parts.filter((_, i) => i !== index))}
          />
        </div>
      ))}
      <p className="type-body-small text-on-surface-variant">
        A namespace of the same catalog. A dot is part of a level&apos;s name.
      </p>
    </fieldset>
  );
}
