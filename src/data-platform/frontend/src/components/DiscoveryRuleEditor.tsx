import { useState } from "react";
import { ruleHasCondition, type DiscoveryRuleDraft } from "@/lib/discoveryPolicyDraft";
import { DISCOVERY_OUTCOME_OPTIONS } from "./forms/discoveryOutcomeOptions";
import { FormDialog } from "./forms/FormDialog";
import { SelectField } from "./forms/SelectField";
import { GlobListField } from "./GlobListField";

const NO_CONDITION_MESSAGE = "A rule needs at least one condition: a namespace or a table name glob.";

interface Props {
  title: string;
  submitLabel: string;
  rule: DiscoveryRuleDraft;
  onSubmit: (rule: DiscoveryRuleDraft) => void;
  onClose: () => void;
}

// Edits one rule of the page's draft; the page saves the whole policy.
export function DiscoveryRuleEditor({ title, submitLabel, rule, onSubmit, onClose }: Props) {
  const [outcome, setOutcome] = useState(rule.outcome);
  const [namespaces, setNamespaces] = useState(rule.namespaces);
  const [tableNames, setTableNames] = useState(rule.tableNames);
  const [invalid, setInvalid] = useState<string | null>(null);

  function submit() {
    const edited = { ...rule, outcome, namespaces, tableNames };
    if (!ruleHasCondition(edited)) {
      setInvalid(NO_CONDITION_MESSAGE);
      return;
    }
    onSubmit(edited);
  }

  return (
    <FormDialog
      title={title}
      description="A table matches when every condition holds; within one, any glob may match. An empty list sets no condition. Save on the page applies the changes."
      submitLabel={submitLabel}
      isPending={false}
      error={invalid}
      onSubmit={submit}
      onClose={onClose}
    >
      <SelectField label="Outcome" value={outcome} options={DISCOVERY_OUTCOME_OPTIONS} onChange={setOutcome} />
      <GlobListField
        label="Namespace"
        hint="Globs on the full dotted namespace: sales.* matches sales.eu."
        globs={namespaces}
        onChange={setNamespaces}
      />
      <GlobListField label="Table name" hint="Globs on the table name, such as orders_*." globs={tableNames} onChange={setTableNames} />
    </FormDialog>
  );
}
