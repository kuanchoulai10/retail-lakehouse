import { actionLabel, type RuleAction } from "@/lib/discoveryPolicyDraft";
import type { SelectOption } from "./SelectField";

// What a discovery rule may do, as every action Select offers it; the words come from `actionLabel` alone.
export const RULE_ACTION_OPTIONS: SelectOption<RuleAction>[] = (["include", "exclude"] as const).map((action) => ({
  value: action,
  label: actionLabel(action),
}));
