// A maintenance priority as the console shows it. A table's own priority orders its maintenance in
// the queue; the old time a compaction round allowed each priority is gone.
export function priorityText(priority: string): string {
  return priority;
}
