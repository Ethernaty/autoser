import type { DataTableColumn } from "@/design-system/primitives/data-table/data-table.types";

export function createColumn<T>(column: DataTableColumn<T>): DataTableColumn<T> {
  return column;
}
