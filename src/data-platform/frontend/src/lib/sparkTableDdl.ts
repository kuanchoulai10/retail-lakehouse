import type { CatalogTableApiResponse } from "@/api/catalogTypes";
import { quoteIdentifier, sparkColumnType } from "./sparkColumnType";

// Spark SQL with the Iceberg runtime, because that is the dialect Iceberg documents its DDL in
// (PARTITIONED BY transforms, WRITE ORDERED BY) and the one the upstream Polaris console shows.
// Trino cannot state partition transforms or sort orders in CREATE TABLE the same way.

// Keys Spark refuses in TBLPROPERTIES; Spark sets them from other clauses.
const RESERVED_KEYS = new Set(["provider", "location", "owner", "external", "comment", "is_managed_location"]);

function quoteText(text: string): string {
  return `'${text.replaceAll("'", "''")}'`;
}

function transformed(transform: string, column: string): string | null {
  const argument = /^(bucket|truncate)\[(\d+)\]$/.exec(transform);
  if (argument !== null) return `${argument[1]}(${argument[2]}, ${column})`;
  switch (transform) {
    case "identity":
      return column;
    case "year":
    case "month":
    case "day":
    case "hour":
      return `${transform}s(${column})`;
    case "void":
      return null;
    default:
      return `${transform}(${column})`;
  }
}

export function sparkTableDdl(table: CatalogTableApiResponse): string {
  const identifier = [table.catalog, ...table.namespace, table.name].map(quoteIdentifier).join(".");
  const columnName = (sourceId: number) =>
    quoteIdentifier(table.schema.fields.find((field) => field.id === sourceId)?.name ?? `${sourceId}`);

  const columns = table.schema.fields.map((field) => {
    const notNull = field.required ? " NOT NULL" : "";
    const comment = field.doc === null || field.doc === "" ? "" : ` COMMENT ${quoteText(field.doc)}`;
    return `  ${quoteIdentifier(field.name)} ${sparkColumnType(field.type)}${notNull}${comment}`;
  });
  const lines = [`CREATE TABLE ${identifier} (`, columns.join(",\n"), ")", "USING iceberg"];

  const partitions = table.partition_spec.fields
    .map((field) => transformed(field.transform, columnName(field.source_id)))
    .filter((term): term is string => term !== null);
  if (partitions.length > 0) lines.push(`PARTITIONED BY (${partitions.join(", ")})`);

  lines.push(`LOCATION ${quoteText(table.location)}`);

  const properties: Record<string, string> = { "format-version": String(table.format_version) };
  for (const [key, value] of Object.entries(table.properties)) {
    if (!RESERVED_KEYS.has(key)) properties[key] = value;
  }
  const entries = Object.entries(properties).sort(([a], [b]) => a.localeCompare(b));
  lines.push("TBLPROPERTIES (", entries.map(([k, v]) => `  ${quoteText(k)} = ${quoteText(v)}`).join(",\n"), ");");

  const sortTerms = table.sort_order.fields.map((field) => {
    const term = transformed(field.transform, columnName(field.source_id)) ?? columnName(field.source_id);
    const nulls = field.null_order === "nulls-first" ? "NULLS FIRST" : "NULLS LAST";
    return `${term} ${field.direction.toUpperCase()} ${nulls}`;
  });
  if (sortTerms.length > 0) {
    lines.push("", `ALTER TABLE ${identifier} WRITE ORDERED BY ${sortTerms.join(", ")};`);
  }
  return lines.join("\n");
}
