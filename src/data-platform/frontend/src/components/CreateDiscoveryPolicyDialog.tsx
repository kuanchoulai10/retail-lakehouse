import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router";
import {
  createTableDiscoveryPolicy,
  getListTableDiscoveryPoliciesQueryKey,
} from "@/api/generated/discovery-policies/discovery-policies";
import type { CreateTableDiscoveryPolicyApiRequest } from "@/api/generated/model";
import { errorMessage } from "@/format";
import type { RuleAction } from "@/lib/discoveryPolicyDraft";
import { discoveryPolicyPath } from "@/lib/discoveryPolicyPaths";
import { POLICY_NAME_PATTERN } from "@/lib/policyDraft";
import { FormDialog } from "./forms/FormDialog";
import { RULE_ACTION_OPTIONS } from "./forms/ruleActionOptions";
import { SelectField } from "./forms/SelectField";
import { TextField } from "./forms/TextField";

const NAME_MESSAGE = "A name uses letters, digits, - and _ only, at most 64 characters.";
const PATTERN_MESSAGE = "The first rule needs a table name pattern.";

interface Props {
  onClose: () => void;
}

// Creates a discovery policy with its first rule, since a policy holds at least one; any further
// rules are written on its own page, where it goes once created. A new policy decides no table
// until it is attached.
export function CreateDiscoveryPolicyDialog({ onClose }: Props) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [action, setAction] = useState<RuleAction>("include");
  const [tableNamePattern, setTableNamePattern] = useState("");
  const [invalid, setInvalid] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: (body: CreateTableDiscoveryPolicyApiRequest) => createTableDiscoveryPolicy(body),
    onSuccess: (created) => {
      onClose();
      navigate(discoveryPolicyPath(created.name));
    },
    // A write can fail after part of it landed, so the list is refetched either way; on a failure
    // the dialog stays open with the API's message.
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: getListTableDiscoveryPoliciesQueryKey(), exact: true });
    },
  });

  function submit() {
    const trimmed = name.trim();
    let problem: string | null = null;
    if (!POLICY_NAME_PATTERN.test(trimmed)) problem = NAME_MESSAGE;
    else if (tableNamePattern.trim() === "") problem = PATTERN_MESSAGE;
    setInvalid(problem);
    if (problem !== null) return;
    create.mutate({ name: trimmed, description, rules: [{ action, table_name_pattern: tableNamePattern }] });
  }

  return (
    <FormDialog
      title="New discovery policy"
      description="Starts with one rule; add more on the policy's page. A new policy decides no table until it is attached."
      submitLabel="Create policy"
      isPending={create.isPending}
      error={invalid ?? (create.isError ? errorMessage(create.error) : null)}
      onSubmit={submit}
      onClose={onClose}
    >
      <TextField
        label="Name"
        mono
        hint="Letters, digits, - and _. A name cannot be changed later."
        value={name}
        onChange={setName}
      />
      <TextField label="Description" value={description} onChange={setDescription} />
      <SelectField label="Action" value={action} options={RULE_ACTION_OPTIONS} onChange={setAction} />
      <TextField
        label="Table name pattern"
        mono
        hint="A glob on the table name alone, such as orders_*."
        value={tableNamePattern}
        onChange={setTableNamePattern}
      />
    </FormDialog>
  );
}
