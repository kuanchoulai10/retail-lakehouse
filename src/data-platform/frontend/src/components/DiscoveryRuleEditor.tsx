import { TextField } from "@retail-lakehouse/design-system";
import { useState } from "react";
import type { DiscoveryRuleAction, DiscoveryRuleDraft } from "@/lib/discoveryRuleDraft";
import { CheckboxField } from "./forms/CheckboxField";
import { FormDialog } from "./forms/FormDialog";
import { SelectField, type SelectOption } from "./forms/SelectField";
import { GlobListField } from "./GlobListField";

const ACTIONS: SelectOption<DiscoveryRuleAction>[] = [
  { value: "include", label: "Include" },
  { value: "exclude", label: "Exclude" },
];

const GLOB_FIELDS = [
  { field: "catalogs", label: "Catalogs", noun: "catalog", hint: "Globs on the catalog name; any one may match." },
  {
    field: "namespaces",
    label: "Namespaces",
    noun: "namespace",
    hint: "Globs on the full dotted name: prod.* matches prod.sales.",
  },
  { field: "tables", label: "Tables", noun: "table", hint: "Globs on the table name; any one may match." },
] as const;

interface Props {
  title: string;
  submitLabel: string;
  rule: DiscoveryRuleDraft;
  onSubmit: (rule: DiscoveryRuleDraft) => void;
  onClose: () => void;
}

// Edits one rule of the page's draft; the page saves the whole list.
export function DiscoveryRuleEditor({ title, submitLabel, rule, onSubmit, onClose }: Props) {
  const [priority, setPriority] = useState(String(rule.priority));
  const [action, setAction] = useState(rule.action);
  const [enabled, setEnabled] = useState(rule.enabled);
  const [globs, setGlobs] = useState({ catalogs: rule.catalogs, namespaces: rule.namespaces, tables: rule.tables });
  const [invalid, setInvalid] = useState<string | null>(null);

  function submit() {
    const trimmed = priority.trim();
    if (!/^-?\d+$/.test(trimmed)) {
      setInvalid("Priority must be a whole number.");
      return;
    }
    const empty = GLOB_FIELDS.find(({ field }) => globs[field].length === 0);
    if (empty !== undefined) {
      setInvalid(`Add at least one ${empty.noun} glob.`);
      return;
    }
    onSubmit({ ...rule, priority: Number(trimmed), action, enabled, ...globs });
  }

  return (
    <FormDialog
      title={title}
      description="A table matches when one glob of each list matches it. Save on the page applies the changes."
      submitLabel={submitLabel}
      isPending={false}
      error={invalid}
      onSubmit={submit}
      onClose={onClose}
    >
      <TextField
        label="Priority"
        description="Lower is applied first. Each rule needs its own."
        type="number"
        inputMode="numeric"
        step={1}
        className="tabular-nums"
        value={priority}
        onChange={(event) => setPriority(event.target.value)}
      />
      <SelectField label="Action" value={action} options={ACTIONS} onChange={setAction} />
      <CheckboxField label="Enabled" checked={enabled} onChange={setEnabled} />
      {GLOB_FIELDS.map(({ field, label, hint }) => (
        <GlobListField
          key={field}
          label={label}
          hint={hint}
          globs={globs[field]}
          onChange={(next) => setGlobs((current) => ({ ...current, [field]: next }))}
        />
      ))}
    </FormDialog>
  );
}
