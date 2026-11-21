import { sentenceCase } from "@/lib/sentenceCase";

const OPERATION_LABELS: Record<string, string> = {
  rewrite_data_files: "Rewrite data files",
  rewrite_manifests: "Rewrite manifests",
  expire_snapshots: "Expire snapshots",
  remove_orphan_files: "Remove orphan files",
};

// A maintenance operation's name as the console shows it; an operation it does not know reads in sentence case.
export function operationLabel(operation: string): string {
  return OPERATION_LABELS[operation] ?? sentenceCase(operation);
}
