import { AlertDialog, AlertDialogCancel, Banner, Button } from "@retail-lakehouse/design-system";
import type { CatalogTablePropertyApiResponse } from "@/api/generated/model";
import { resetDeletesProperty } from "@/lib/resetDeletesProperty";

interface Props {
  fullPath: string;
  // The modified, resettable properties the reset covers; custom ones with no default are deleted.
  properties: CatalogTablePropertyApiResponse[];
  isPending: boolean;
  error: string | null;
  onConfirm: () => void;
  onClose: () => void;
}

function count(n: number, one: string, many: string): string {
  return `${n} ${n === 1 ? one : many}`;
}

// Reset all changes every modified property at once, so it names each key and asks first. It asks
// for no typed name like a delete of a catalog object: every key it changes is listed here.
export function ResetAllPropertiesDialog({ fullPath, properties, isPending, error, onConfirm, onClose }: Props) {
  const custom = properties.filter(resetDeletesProperty).length;
  const known = properties.length - custom;
  const what = [
    known > 0 && `resets ${count(known, "property", "properties")} to default`,
    custom > 0 && `deletes ${count(custom, "custom property", "custom properties")}`,
  ]
    .filter(Boolean)
    .join(" and ");
  return (
    <AlertDialog
      isOpen
      onOpenChange={(open) => !open && onClose()}
      title="Reset all to default"
      description={
        <>
          This {what} of <span className="font-mono">{fullPath}</span>. Maintenance reads some properties,
          such as the target file size, so its next run follows the new values.
        </>
      }
      footer={
        <>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <Button type="button" styleType="negative" disabled={isPending} onClick={onConfirm}>
            Reset all
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <ul className="flex flex-col gap-1">
          {properties.map((p) => (
            <li key={p.key} className="type-code break-all">
              {p.key}
            </li>
          ))}
        </ul>
        {error !== null && <Banner type="negative" title={error} />}
      </div>
    </AlertDialog>
  );
}
