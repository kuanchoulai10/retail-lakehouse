import { Switch } from "@retail-lakehouse/design-system";
import { Fragment, type ReactNode } from "react";
import type { CompactionScopeApiRequestUnit } from "@/api/generated/model";
import { SelectField, type SelectOption } from "./forms/SelectField";
import { WholeNumberField, type WholeNumberInput } from "./forms/WholeNumberField";

// One condition of a trigger policy: its threshold fields, all empty when it is not checked.
export interface TriggerCondition {
  label: string;
  fields: WholeNumberInput[];
}

const SCOPES: SelectOption<CompactionScopeApiRequestUnit>[] = [
  { value: "partition", label: "Each partition" },
  { value: "table", label: "Whole table" },
];

interface Props {
  title: string;
  enabled: boolean;
  onEnabledChange: (enabled: boolean) => void;
  // Only rewrite data files has one; both its trigger and its execution follow it.
  scope?: { value: CompactionScopeApiRequestUnit; onChange: (unit: CompactionScopeApiRequestUnit) => void };
  cooldown: WholeNumberInput;
  conditions: TriggerCondition[];
  // The execution policy's fields; none means the procedure runs with its own defaults.
  children?: ReactNode;
}

function Group({ legend, children }: { legend: string; children: ReactNode }) {
  return (
    <fieldset className="flex min-w-0 flex-col gap-3 rounded-md border border-outline p-3">
      <legend className="type-title-small px-1 text-on-surface">{legend}</legend>
      {children}
    </fieldset>
  );
}

// One operation of a policy: its switch and scope, then when it is due ("Trigger") apart from
// what the Iceberg procedure is given ("Execution"), as the policy itself keeps them apart.
export function OperationPolicySection({
  title,
  enabled,
  onEnabledChange,
  scope,
  cooldown,
  conditions,
  children,
}: Props) {
  return (
    <fieldset className="flex min-w-0 flex-col gap-3 border-t border-outline pt-3">
      <legend className="type-title-medium text-on-surface">{title}</legend>
      <Switch label="Enabled" checked={enabled} onCheckedChange={onEnabledChange} />
      {scope !== undefined && (
        <SelectField label="Scope" value={scope.value} options={SCOPES} onChange={scope.onChange} />
      )}
      <Group legend="Trigger">
        <WholeNumberField {...cooldown} />
        {conditions.length === 0 ? (
          <p className="type-body-small text-on-surface-variant">No conditions: due once the cooldown has passed.</p>
        ) : (
          <>
            <p className="type-body-small text-on-surface-variant">
              Due once the cooldown has passed and any condition holds. An empty condition is not checked; with
              none set, the cooldown alone decides.
            </p>
            {conditions.map((condition, index) => (
              <Fragment key={condition.label}>
                {index > 0 && <p className="type-label-large text-on-surface-variant">or</p>}
                <div role="group" aria-label={condition.label} className="flex flex-col gap-3">
                  {condition.fields.map((field) => (
                    <WholeNumberField key={field.label} {...field} />
                  ))}
                </div>
              </Fragment>
            ))}
          </>
        )}
      </Group>
      <Group legend="Execution">
        {children ?? (
          <p className="type-body-small text-on-surface-variant">Nothing to set: the procedure uses its defaults.</p>
        )}
      </Group>
    </fieldset>
  );
}
