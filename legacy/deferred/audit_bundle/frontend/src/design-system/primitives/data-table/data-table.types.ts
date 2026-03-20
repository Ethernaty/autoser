import type { ReactNode } from "react";

export type TableAlign = "left" | "center" | "right";
export type SortDirection = "asc" | "desc";

export type DataTableSort = {
  key: string;
  direction: SortDirection;
};

export type DataTableColumn<T> = {
  id: string;
  header: ReactNode;
  cell: (row: T) => ReactNode;
  align?: TableAlign;
  width?: number;
  minWidth?: number;
  sortable?: boolean;
  sortKey?: string;
};

export type DataTableSelection = {
  selectedIds: Set<string>;
  onToggle: (rowId: string) => void;
  onToggleAll: (rowIds: string[], checked: boolean) => void;
};

export type DataTableActionVariant = "secondary" | "ghost" | "destructive";

export type DataTableRowAction<T> = {
  id: string;
  label: string;
  onClick: (row: T) => void;
  variant?: DataTableActionVariant;
  hidden?: (row: T) => boolean;
  disabled?: (row: T) => boolean;
};

export type DataTableBulkAction = {
  id: string;
  label: string;
  onClick: (selectedIds: string[]) => void;
  variant?: DataTableActionVariant;
};

export type DataTablePagination = {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
};

