import type { JsonObject, TableMetadataApiResponse } from "../api/types";

function fieldsOf(spec: JsonObject | undefined): JsonObject[] {
  return Array.isArray(spec?.fields) ? (spec.fields as JsonObject[]) : [];
}

export function SchemaPanel({ metadata }: { metadata: TableMetadataApiResponse }) {
  const partitionFields = fieldsOf(metadata.specs.at(-1));
  return (
    <section className="panel" aria-label="Schema">
      <h2>Schema</h2>
      <table className="data-table">
        <thead>
          <tr>
            <th>Column</th>
            <th>Type</th>
            <th>Required</th>
          </tr>
        </thead>
        <tbody>
          {metadata.schema_fields.map((field) => (
            <tr key={String(field.field_id)}>
              <td>{String(field.name)}</td>
              <td>{String(field.type)}</td>
              <td>{field.required ? "yes" : "no"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h3>Partition spec</h3>
      {partitionFields.length === 0 ? (
        <p className="muted">Unpartitioned.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Field</th>
              <th>Source column</th>
              <th>Transform</th>
            </tr>
          </thead>
          <tbody>
            {partitionFields.map((field) => (
              <tr key={String(field.field_id)}>
                <td>{String(field.name)}</td>
                <td>{String(field.source_column)}</td>
                <td>{String(field.transform)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
