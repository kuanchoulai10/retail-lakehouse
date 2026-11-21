import { outcomeLabel, type DiscoveryOutcome } from "@/lib/discoveryPolicyDraft";
import type { SelectOption } from "./SelectField";

// What a discovery rule or a policy's no-match outcome may decide, as every outcome Select offers it;
// the words come from `outcomeLabel` alone.
export const DISCOVERY_OUTCOME_OPTIONS: SelectOption<DiscoveryOutcome>[] = (["manage", "unmanage"] as const).map(
  (outcome) => ({ value: outcome, label: outcomeLabel(outcome) }),
);
