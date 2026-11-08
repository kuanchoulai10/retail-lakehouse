import { createColumnHelper, type RowData } from "@tanstack/react-table";
import type { DataTableFeatures } from "./dataTableFeatures";

export function createDataTableColumnHelper<T extends RowData>() {
  return createColumnHelper<DataTableFeatures, T>();
}
