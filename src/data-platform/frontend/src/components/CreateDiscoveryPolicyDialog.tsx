import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router";
import {
  createTableDiscoveryPolicy,
  getListTableDiscoveryPoliciesQueryKey,
} from "@/api/generated/discovery-policies/discovery-policies";
import type {
  CreateTableDiscoveryPolicyApiRequest,
  CreateTableDiscoveryPolicyApiRequestNoMatchOutcome,
} from "@/api/generated/model";
import { errorMessage } from "@/format";
import { discoveryPolicyPath } from "@/lib/discoveryPolicyPaths";
import { POLICY_NAME_PATTERN } from "@/lib/policyDraft";
import { FormDialog } from "./forms/FormDialog";
import { SelectField, type SelectOption } from "./forms/SelectField";
import { TextField } from "./forms/TextField";

const NAME_MESSAGE = "A name uses letters, digits, - and _ only, at most 64 characters.";
const NO_MATCH_OUTCOMES: SelectOption<CreateTableDiscoveryPolicyApiRequestNoMatchOutcome>[] = [
  { value: "manage", label: "Manage" },
  { value: "unmanage", label: "Do not manage" },
];

interface Props {
  onClose: () => void;
}

// Creates a discovery policy with no rules; its rules are written on its own page, where it
// goes once created. A new policy decides no table until it is attached.
export function CreateDiscoveryPolicyDialog({ onClose }: Props) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [noMatchOutcome, setNoMatchOutcome] = useState<CreateTableDiscoveryPolicyApiRequestNoMatchOutcome>("unmanage");
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
    const problem = POLICY_NAME_PATTERN.test(trimmed) ? null : NAME_MESSAGE;
    setInvalid(problem);
    if (problem !== null) return;
    create.mutate({ name: trimmed, description, no_match_outcome: noMatchOutcome, rules: [] });
  }

  return (
    <FormDialog
      title="New discovery policy"
      description="Starts with no rules; add them on the policy's page. A new policy decides no table until it is attached."
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
      <SelectField
        label="When no rule matches"
        value={noMatchOutcome}
        options={NO_MATCH_OUTCOMES}
        onChange={setNoMatchOutcome}
      />
    </FormDialog>
  );
}
