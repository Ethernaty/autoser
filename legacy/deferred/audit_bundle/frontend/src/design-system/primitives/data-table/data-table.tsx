"use client";

import { ChevronDown, ChevronLeft, ChevronRight, ChevronUp } from "lucide-react";
import { useMemo, useRef } from "react";

import { cn } from "@/core/lib/utils";
import { Button } from "@/design-system/primitives/button";
import type {
  DataTableBulkAction,
  DataTableColumn,
  DataTablePagination,
  DataTableRowAction,
  DataTableSelection,
  DataTableSort,
  SortDirection
} from "@/design-system/primitives/data-table/data-table.types";
import { useRovingFocus } from "@/shared/hooks/use-roving-focus";

export type DataTableProps<T> = {
  columns: DataTableColumn<T>[];
  rows: T[];
  getRowId: (row: T) => string;
  sort?: DataTableSort;
  onSortChange?: (value: DataTableSort) => void;
  selection?: DataTableSelection;
  rowActions?: DataTableRowAction<T>[];
  bulkActions?: DataTableBulkAction[];
  pagination?: DataTablePagination;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  emptyTitle?: string;
  emptyDescription?: string;
  density?: "comfortable" | "compact";
};

function nextDirection(current?: SortDirection): SortDirection {
  return current === "asc" ? "desc" : "asc";
}

function alignClass(align: "left" | "center" | "right" | undefined): string {
  if (align === "center") {
    return "text-center";
  }
  if (align === "right") {
    return "text-right";
  }
  return "text-left";
}

export function DataTable<T>({
  columns,
  rows,
  getRowId,
  sort,
  onSortChange,
  selection,
  rowActions,
  bulkActions,
  pagination,
  loading = false,
  error,
  onRetry,
  emptyTitle = "No records found",
  emptyDescription = "Change filters or create a new record.",
  density = "compact"
}: DataTableProps<T>): JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);
  useRovingFocus({ container: containerRef, selector: "tbody tr[role='row']" });

  const rowClass = density === "compact" ? "h-5" : "h-6";
  const rowIds = useMemo(() => rows.map((row) => getRowId(row)), [rows, getRowId]);
  const hasActions = Boolean(rowActions?.length);

  const allSelected = selection ? rowIds.length > 0 && rowIds.every((id) => selection.selectedIds.has(id)) : false;
  const selectedCount = selection ? rowIds.filter((id) => selection.selectedIds.has(id)).length : 0;

  const totalColumns = columns.length + (selection ? 1 : 0) + (hasActions ? 1 : 0);
  const totalPages = pagination ? Math.max(1, Math.ceil(pagination.total / pagination.pageSize)) : 1;

  return (
    <div className="overflow-hidden rounded-md border border-neutral-200 bg-neutral-0" data-keyboard-nav="true" ref={containerRef}>
      {selection && selectedCount > 0 ? (
        <div className="flex flex-wrap items-center justify-between gap-1 border-b border-neutral-200 bg-neutral-50 px-2 py-1">
          <p className="text-sm text-neutral-700">Selected: {selectedCount}</p>
          <div className="flex flex-wrap items-center gap-1">
            {(bulkActions ?? []).map((action) => (
              <Button
                key={action.id}
                size="sm"
                variant={action.variant ?? "secondary"}
                onClick={() => action.onClick(Array.from(selection.selectedIds))}
              >
                {action.label}
              </Button>
            ))}
          </div>
        </div>
      ) : null}

      <div className="max-h-[640px] overflow-auto">
        <table className="w-full min-w-[960px] border-separate border-spacing-0" role="grid">
          <thead className="sticky top-0 z-10 bg-neutral-50">
            <tr>
              {selection ? (
                <th className="h-5 w-4 border-b border-neutral-200 px-2">
                  <input
                    type="checkbox"
                    aria-label="Select all rows"
                    checked={allSelected}
                    onChange={(event) => selection.onToggleAll(rowIds, event.target.checked)}
                  />
                </th>
              ) : null}
              {columns.map((column) => {
                const sortKey = column.sortKey ?? column.id;
                const active = sort?.key === sortKey;

                return (
                  <th
                    key={column.id}
                    className={cn(
                      "h-5 border-b border-neutral-200 px-2 text-xs font-semibold uppercase tracking-wide text-neutral-600",
                      alignClass(column.align)
                    )}
                    style={{ width: column.width, minWidth: column.minWidth }}
                  >
                    {column.sortable && onSortChange ? (
                      <button
                        type="button"
                        className="inline-flex items-center gap-1"
                        onClick={() =>
                          onSortChange({
                            key: sortKey,
                            direction: nextDirection(active ? sort?.direction : undefined)
                          })
                        }
                      >
                        {column.header}
                        {active ? sort?.direction === "asc" ? <ChevronUp className="h-2.5 w-2.5" /> : <ChevronDown className="h-2.5 w-2.5" /> : null}
                      </button>
                    ) : (
                      column.header
                    )}
                  </th>
                );
              })}
              {hasActions ? <th className="h-5 border-b border-neutral-200 px-2 text-right text-xs font-semibold uppercase tracking-wide text-neutral-600">Actions</th> : null}
            </tr>
          </thead>
          <tbody>
            {loading
              ? Array.from({ length: 8 }).map((_, index) => (
                  <tr key={`skeleton-${index}`} role="row" className={rowClass}>
                    {Array.from({ length: totalColumns }).map((__, cellIndex) => (
                      <td key={`skeleton-cell-${index}-${cellIndex}`} className="border-b border-neutral-100 px-2">
                        <div className="h-2 w-full animate-pulse rounded bg-neutral-100" />
                      </td>
                    ))}
                  </tr>
                ))
              : null}

            {!loading && error ? (
              <tr>
                <td colSpan={totalColumns} className="border-b border-neutral-100 px-2 py-3">
                  <div className="flex flex-wrap items-center justify-between gap-2 rounded-sm border border-error/25 bg-error/5 p-2">
                    <div>
                      <p className="text-sm font-medium text-error">Unable to load table data</p>
                      <p className="text-xs text-neutral-700">{error}</p>
                    </div>
                    {onRetry ? (
                      <Button variant="secondary" size="sm" onClick={onRetry}>
                        Retry
                      </Button>
                    ) : null}
                  </div>
                </td>
              </tr>
            ) : null}

            {!loading && !error && rows.length === 0 ? (
              <tr>
                <td colSpan={totalColumns} className="border-b border-neutral-100 px-2 py-4 text-center">
                  <p className="text-sm font-medium text-neutral-800">{emptyTitle}</p>
                  <p className="mt-1 text-sm text-neutral-600">{emptyDescription}</p>
                </td>
              </tr>
            ) : null}

            {!loading && !error
              ? rows.map((row, index) => {
                  const rowId = getRowId(row);
                  const selected = selection?.selectedIds.has(rowId) ?? false;

                  return (
                    <tr
                      key={rowId}
                      role="row"
                      tabIndex={index === 0 ? 0 : -1}
                      className={cn(rowClass, "group border-b border-neutral-100 hover:bg-neutral-50", selected && "bg-primary/5")}
                    >
                      {selection ? (
                        <td className="border-b border-neutral-100 px-2 align-middle">
                          <input aria-label={`Select row ${rowId}`} type="checkbox" checked={selected} onChange={() => selection.onToggle(rowId)} />
                        </td>
                      ) : null}
                      {columns.map((column) => (
                        <td key={column.id} role="gridcell" className={cn("border-b border-neutral-100 px-2 text-sm text-neutral-800", alignClass(column.align))}>
                          {column.cell(row)}
                        </td>
                      ))}
                      {hasActions ? (
                        <td className="border-b border-neutral-100 px-2 text-right">
                          <div className="inline-flex items-center gap-1">
                            {rowActions
                              ?.filter((action) => (action.hidden ? !action.hidden(row) : true))
                              .map((action) => (
                                <Button
                                  key={action.id}
                                  size="sm"
                                  variant={action.variant ?? "ghost"}
                                  onClick={() => action.onClick(row)}
                                  disabled={action.disabled ? action.disabled(row) : false}
                                >
                                  {action.label}
                                </Button>
                              ))}
                          </div>
                        </td>
                      ) : null}
                    </tr>
                  );
                })
              : null}
          </tbody>
        </table>
      </div>

      {pagination ? (
        <div className="flex items-center justify-between gap-2 border-t border-neutral-200 px-2 py-1.5">
          <p className="text-xs text-neutral-600">
            Showing {(pagination.page - 1) * pagination.pageSize + 1}-{Math.min(pagination.page * pagination.pageSize, pagination.total)} of {pagination.total}
          </p>
          <div className="flex items-center gap-1">
            <Button
              size="sm"
              variant="secondary"
              onClick={() => pagination.onPageChange(Math.max(1, pagination.page - 1))}
              disabled={pagination.page <= 1}
            >
              <ChevronLeft className="h-2.5 w-2.5" />
              Prev
            </Button>
            <span className="text-xs text-neutral-700">
              Page {pagination.page}/{totalPages}
            </span>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => pagination.onPageChange(Math.min(totalPages, pagination.page + 1))}
              disabled={pagination.page >= totalPages}
            >
              Next
              <ChevronRight className="h-2.5 w-2.5" />
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

