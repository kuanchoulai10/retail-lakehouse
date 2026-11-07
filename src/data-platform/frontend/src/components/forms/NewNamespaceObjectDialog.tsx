import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { CreateGenericTableDialog } from "./CreateGenericTableDialog";
import { CreateTableDialog } from "./CreateTableDialog";
import { CreateViewDialog } from "./CreateViewDialog";

type ObjectKind = "table" | "view" | "generic-table";

const CHOICES: { kind: ObjectKind; label: string; hint: string }[] = [
  { kind: "table", label: "Table", hint: "An Iceberg table with a schema." },
  { kind: "view", label: "View", hint: "An Iceberg view defined by SQL." },
  { kind: "generic-table", label: "Generic table", hint: "A table in another format, such as Delta." },
];

interface Props {
  catalog: string;
  namespace: string[];
  onClose: () => void;
}

// The New button of the namespace's one list: pick the kind, then fill in its form.
export function NewNamespaceObjectDialog({ catalog, namespace, onClose }: Props) {
  const [kind, setKind] = useState<ObjectKind | null>(null);
  if (kind === "table") return <CreateTableDialog catalog={catalog} namespace={namespace} onClose={onClose} />;
  if (kind === "view") return <CreateViewDialog catalog={catalog} namespace={namespace} onClose={onClose} />;
  if (kind === "generic-table") {
    return <CreateGenericTableDialog catalog={catalog} namespace={namespace} onClose={onClose} />;
  }
  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New table or view</DialogTitle>
          <DialogDescription>Choose what to create.</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-2">
          {CHOICES.map((choice) => (
            <div key={choice.kind} className="flex items-center justify-between gap-3">
              <span className="text-sm text-muted-foreground">{choice.hint}</span>
              <Button type="button" variant="outline" className="w-32" onClick={() => setKind(choice.kind)}>
                {choice.label}
              </Button>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
