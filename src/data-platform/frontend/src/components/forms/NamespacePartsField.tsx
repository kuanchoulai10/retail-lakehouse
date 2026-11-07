import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface Props {
  parts: string[];
  onChange: (parts: string[]) => void;
}

// One input per namespace level, so a dot stays part of a level's name ("a.b" is one level).
export function NamespacePartsField({ parts, onChange }: Props) {
  return (
    <fieldset className="m-0 flex min-w-0 flex-col gap-2 border-0 p-0">
      <div className="flex items-center justify-between">
        <legend className="text-sm font-medium">Namespace</legend>
        <Button type="button" variant="outline" size="sm" onClick={() => onChange([...parts, ""])}>
          Add level
        </Button>
      </div>
      {parts.map((part, index) => (
        <div key={index} className="flex items-center gap-2">
          <Input
            aria-label={`Namespace level ${index + 1}`}
            className="font-mono text-[13px]"
            autoComplete="off"
            value={part}
            onChange={(event) => onChange(parts.map((p, i) => (i === index ? event.target.value : p)))}
          />
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label={`Remove level ${index + 1}`}
            disabled={parts.length === 1}
            onClick={() => onChange(parts.filter((_, i) => i !== index))}
          >
            <X aria-hidden="true" />
          </Button>
        </div>
      ))}
      <p className="text-xs text-muted-foreground">
        A namespace of the same catalog. A dot is part of a level&apos;s name.
      </p>
    </fieldset>
  );
}
