import { Switch } from "@retail-lakehouse/design-system";
import type { ReactNode } from "react";

interface Props {
  title: string;
  included: boolean;
  onIncludedChange: (included: boolean) => void;
  // The state the table is kept in: what the check compares the table with.
  target: ReactNode;
  // What the Iceberg procedure is given when it runs.
  options: ReactNode;
}

function Group({ legend, children }: { legend: string; children: ReactNode }) {
  return (
    <fieldset className="flex min-w-0 flex-col gap-3 rounded-md border border-outline p-3">
      <legend className="type-title-small px-1 text-on-surface">{legend}</legend>
      {children}
    </fieldset>
  );
}

// One operation of a policy: whether the policy holds it, then the target the table is kept at
// apart from the options the procedure runs with, as the policy itself keeps them apart.
export function OperationPolicySection({ title, included, onIncludedChange, target, options }: Props) {
  return (
    <fieldset className="flex min-w-0 flex-col gap-3 border-t border-outline pt-3">
      <legend className="type-title-medium text-on-surface">{title}</legend>
      <Switch label="In this policy" checked={included} onCheckedChange={onIncludedChange} />
      {included ? (
        <>
          <Group legend="Target">{target}</Group>
          <Group legend="Options">
            <p className="type-body-small text-on-surface-variant">Empty: the procedure&apos;s default.</p>
            {options}
          </Group>
        </>
      ) : (
        <p className="type-body-small text-on-surface-variant">
          Not in this policy: this operation does not run on a schedule.
        </p>
      )}
    </fieldset>
  );
}
