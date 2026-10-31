import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router";
import { ApiError, apiGet } from "../api/client";
import type { TableApiResponse } from "../api/types";

const STATUSES = ["ACTIVE", "PAUSED", "EXCLUDED", "DROPPED"] as const;

function fullName(table: TableApiResponse): string {
  return `${table.catalog}.${table.namespace}.${table.table}`;
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.detail;
  if (error instanceof Error) return error.message;
  return String(error);
}

export function TableListPage() {
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const tables = useQuery({
    queryKey: ["tables"],
    queryFn: () => apiGet<TableApiResponse[]>("/v1/tables"),
  });

  const rows = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return (tables.data ?? [])
      .filter((t) => status === "" || t.status.toUpperCase() === status)
      .filter((t) => needle === "" || fullName(t).toLowerCase().includes(needle))
      .sort((a, b) => fullName(a).localeCompare(fullName(b)));
  }, [tables.data, status, search]);

  return (
    <section>
      <h1>Tables</h1>
      <div className="filters">
        <label>
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label>
          Search
          <input
            type="search"
            placeholder="catalog.namespace.table"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
      </div>
      {tables.isPending && <p>Loading tables…</p>}
      {tables.isError && (
        <p role="alert" className="error">
          Could not load tables: {errorMessage(tables.error)}
        </p>
      )}
      {tables.isSuccess && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Status</th>
              <th>Selection</th>
              <th>Source preset</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => (
              <tr key={t.uuid}>
                <td>
                  <Link to={`/tables/${t.uuid}`}>{fullName(t)}</Link>
                </td>
                <td>
                  <span className={`badge badge-${t.status.toLowerCase()}`}>{t.status.toUpperCase()}</span>
                </td>
                <td>{t.selection}</td>
                <td>{t.source_preset_id ?? "—"}</td>
                <td>
                  <time dateTime={t.updated_at}>{formatTimestamp(t.updated_at)}</time>
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={5} className="empty">
                  No tables match.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </section>
  );
}
