import type { TableCommitApiResponse } from "@/api/generated/model";
import { formatCount } from "@/format";

function counted(value: number, noun: string): string {
  return `${formatCount(value)} ${noun}${value === 1 ? "" : "s"}`;
}

// What a commit changed, in the words of a commit message: "1,200 rows added in 4 files".
export function changeSummary(commit: TableCommitApiResponse): string[] {
  const changes: string[] = [];
  const sides = [
    { rows: commit.added_records, files: commit.added_data_files, verb: "added", preposition: "in" },
    { rows: commit.deleted_records, files: commit.deleted_data_files, verb: "removed", preposition: "from" },
  ];
  for (const { rows, files, verb, preposition } of sides) {
    const fileCount = files ?? 0;
    if (rows) {
      const where = fileCount > 0 ? ` ${preposition} ${counted(fileCount, "file")}` : "";
      changes.push(`${counted(rows, "row")} ${verb}${where}`);
    } else if (fileCount > 0) {
      changes.push(`${counted(fileCount, "file")} ${verb}`);
    }
  }
  return changes;
}

export function commitTitle(commit: TableCommitApiResponse): string {
  const operation = commit.operation ?? "commit";
  const name = operation.charAt(0).toUpperCase() + operation.slice(1);
  const changes = changeSummary(commit);
  return changes.length > 0 ? `${name}: ${changes.join(", ")}` : name;
}
