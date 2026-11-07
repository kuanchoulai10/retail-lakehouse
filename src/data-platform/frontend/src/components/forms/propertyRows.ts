export interface PropertyRow {
  key: string;
  value: string;
}

export function rowsFromProperties(properties: Record<string, string>): PropertyRow[] {
  return Object.entries(properties)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, value]) => ({ key, value }));
}

// Rows with a blank key are ignored; a later row wins over an earlier one with the same key.
export function propertiesFromRows(rows: PropertyRow[]): Record<string, string> {
  const properties: Record<string, string> = {};
  for (const row of rows) {
    const key = row.key.trim();
    if (key !== "") properties[key] = row.value;
  }
  return properties;
}

export interface PropertyChanges {
  updates: Record<string, string>;
  removals: string[];
}

// What to send to turn `before` into the edited rows: changed or new keys, and dropped keys.
export function propertyChanges(before: Record<string, string>, rows: PropertyRow[]): PropertyChanges {
  const after = propertiesFromRows(rows);
  const updates: Record<string, string> = {};
  for (const [key, value] of Object.entries(after)) {
    if (before[key] !== value) updates[key] = value;
  }
  const removals = Object.keys(before).filter((key) => !(key in after));
  return { updates, removals };
}
