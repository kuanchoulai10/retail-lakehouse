import type { TableMetadataApiResponse } from "../../api/types";

export function PropertiesTab({ metadata }: { metadata: TableMetadataApiResponse }) {
  const properties = Object.entries(metadata.properties).sort(([a], [b]) => a.localeCompare(b));
  return (
    <>
      <dl className="facts">
        <dt>Format version</dt>
        <dd>{metadata.format_version}</dd>
        <dt>Location</dt>
        <dd>
          <code>{metadata.location}</code>
        </dd>
      </dl>
      <table className="data-table">
        <thead>
          <tr>
            <th>Property</th>
            <th>Value</th>
          </tr>
        </thead>
        <tbody>
          {properties.map(([key, value]) => (
            <tr key={key}>
              <td>{key}</td>
              <td>{value}</td>
            </tr>
          ))}
          {properties.length === 0 && (
            <tr>
              <td colSpan={2} className="empty">
                No properties.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </>
  );
}
