"use client";

import { ChevronDown, ChevronLeft, ChevronRight, ChevronUp } from "lucide-react";
import { type ReactNode, useMemo, useRef } from "react";

import { cn } from "@/core/lib/utils";
import { Button } from "@/design-system/primitives/button";
import type {
  DataTableBulkAction,
  DataTableColumn,
  DataTablePagination,
  DataTableRowAction,
  DataTableSelection,
  DataTableSort,
  DataTableVariant,
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
  emptyAction?: ReactNode;
  tableClassName?: string;
  density?: "comfortable" | "compact";
  variant?: DataTableVariant;
  onRowClick?: (row: T) => void;
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
  emptyAction,
  tableClassName,
  density = "compact",
  variant = "default",
  onRowClick
}: DataTableProps<T>): JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);
  useRovingFocus({ container: containerRef, selector: "tbody tr[role='row']" });

  const strongVariant = variant === "strong";
  const rowClass = density === "compact" ? "h-10" : "h-11";
  const rowIds = useMemo(() => rows.map((row) => getRowId(row)), [rows, getRowId]);
  const hasActions = Boolean(rowActions?.length);

  const allSelected = selection ? rowIds.length > 0 && rowIds.every((id) => selection.selectedIds.has(id)) : false;
  const selectedCount = selection ? rowIds.filter((id) => selection.selectedIds.has(id)).length : 0;

  const totalColumns = columns.length + (selection ? 1 : 0) + (hasActions ? 1 : 0);
  const totalPages = pagination ? Math.max(1, Math.ceil(pagination.total / pagination.pageSize)) : 1;
  const borderColorClass = strongVariant ? "border-neutral-300" : "border-neutral-200";
  const rowBorderClass = strongVariant ? "border-neutral-200" : "border-neutral-100";
  const footerToneClass = strongVariant ? "bg-neutral-100" : "bg-neutral-50";

  return (
    <div
      className={cn(
        "overflow-hidden rounded-lg border bg-neutral-0",
        borderColorClass,
        strongVariant ? "shadow-md" : "shadow-sm"
      )}
      data-keyboard-nav="true"
      ref={containerRef}
    >
      {selection && selectedCount > 0 ? (
        <div className={cn("flex flex-wrap items-center justify-between gap-2 border-b px-3 py-2", borderColorClass, footerToneClass)}>
          <p className="text-sm text-neutral-700">Selected: {selectedCount}</p>
          <div className="flex flex-wrap items-center gap-2">
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
        <table className={cn("w-full min-w-[1040px] border-separate border-spacing-0", tableClassName)} role="grid">
          <thead
            className={cn(
              "sticky top-0 z-10 backdrop-blur",
              strongVariant
                ? "bg-neutral-100/95 supports-[backdrop-filter]:bg-neutral-100/85"
                : "bg-neutral-50/95 supports-[backdrop-filter]:bg-neutral-50/80"
            )}
          >
            <tr>
              {selection ? (
                <th className={cn("h-9 w-10 border-b px-3 align-middle", borderColorClass)}>
                  <input
                    type="checkbox"
                    aria-label="Select all rows"
                    checked={allSelected}
                    onClick={(event) => event.stopPropagation()}
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
                      "h-9 border-b px-3 text-[11px] font-semibold uppercase tracking-wide align-middle",
                      borderColorClass,
                      strongVariant ? "text-neutral-700" : "text-neutral-600",
                      alignClass(column.align)
                    )}
                    style={{ width: column.width, minWidth: column.minWidth }}
                  >
                    {column.sortable && onSortChange ? (
                      <button
                        type="button"
                        className={cn(
                          "inline-flex items-center gap-1.5 rounded-sm px-1 py-0.5",
                          strongVariant ? "hover:bg-neutral-200" : "hover:bg-neutral-100"
                        )}
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
              {hasActions ? (
                <th
                  className={cn(
                    "h-9 border-b px-3 text-right text-[11px] font-semibold uppercase tracking-wide",
                    borderColorClass,
                    strongVariant ? "text-neutral-700" : "text-neutral-600"
                  )}
                >
                  Actions
                </th>
              ) : null}
            </tr>
          </thead>
          <tbody>
            {loading
              ? Array.from({ length: 8 }).map((_, index) => (
                  <tr key={`skeleton-${index}`} role="row" className={rowClass}>
                    {Array.from({ length: totalColumns }).map((__, cellIndex) => (
                      <td key={`skeleton-cell-${index}-${cellIndex}`} className={cn("border-b px-3 py-2", rowBorderClass)}>
                        <div className={cn("h-2.5 w-full animate-pulse rounded", strongVariant ? "bg-neutral-200" : "bg-neutral-100")} />
                      </td>
                    ))}
                  </tr>
                ))
              : null}

            {!loading && error ? (
              <tr>
                <td colSpan={totalColumns} className={cn("border-b px-3 py-4", rowBorderClass)}>
                  <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-error/25 bg-error/5 p-3">
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
                <td colSpan={totalColumns} className={cn("border-b px-3 py-8", rowBorderClass)}>
                  <div className="mx-auto max-w-md rounded-md border border-neutral-200 bg-neutral-50 px-4 py-4 text-center">
                    <p className="text-sm font-semibold text-neutral-800">{emptyTitle}</p>
                    <p className="mt-1 text-sm text-neutral-600">{emptyDescription}</p>
                    {emptyAction ? <div className="mt-3 flex justify-center">{emptyAction}</div> : null}
                  </div>
                </td>
              </tr>
            ) : null}

            {!loading && !error
              ? rows.map((row, index) => {
                  const rowId = getRowId(row);
                  const selected = selection?.selectedIds.has(rowId) ?? false;
                  const isClickable = Boolean(onRowClick);

                  return (
                    <tr
                      key={rowId}
                      role="row"
                      tabIndex={index === 0 ? 0 : -1}
                      className={cn(
                        rowClass,
                        "group border-b transition-colors",
                        rowBorderClass,
                        strongVariant ? "hover:bg-neutral-50/80" : "hover:bg-neutral-50",
                        isClickable && "cursor-pointer focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary/35",
                        isClickable && (strongVariant ? "hover:bg-primary/5" : "hover:bg-primary/5"),
                        selected && "bg-primary/5"
                      )}
                      onClick={isClickable ? () => onRowClick?.(row) : undefined}
                      onKeyDown={
                        isClickable
                          ? (event) => {
                              if (event.key === "Enter" || event.key === " ") {
                                event.preventDefault();
                                onRowClick?.(row);
                              }
                            }
                          : undefined
                      }
                    >
                      {selection ? (
                        <td className={cn("border-b px-3 align-middle", rowBorderClass)}>
                          <input
                            aria-label={`Select row ${rowId}`}
                            type="checkbox"
                            checked={selected}
                            onClick={(event) => event.stopPropagation()}
                            onChange={() => selection.onToggle(rowId)}
                          />
                        </td>
                      ) : null}
                      {columns.map((column) => (
                        <td
                          key={column.id}
                          role="gridcell"
                          className={cn("border-b px-3 py-2 text-sm text-neutral-800", rowBorderClass, alignClass(column.align))}
                        >
                          {column.cell(row)}
                        </td>
                      ))}
                      {hasActions ? (
                        <td className={cn("border-b px-3 text-right align-middle", rowBorderClass)}>
                          <div className="inline-flex items-center gap-1.5 whitespace-nowrap">
                            {rowActions
                              ?.filter((action) => (action.hidden ? !action.hidden(row) : true))
                              .map((action) => (
                                <Button
                                  key={action.id}
                                  size="sm"
                                  variant={action.variant ?? "ghost"}
                                  className="h-8"
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    action.onClick(row);
                                  }}
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
        <div className={cn("flex items-center justify-between gap-3 border-t px-3 py-2", borderColorClass, footerToneClass)}>
          <p className="text-xs text-neutral-600">
            {pagination.total === 0
              ? "Showing 0 of 0"
              : `Showing ${(pagination.page - 1) * pagination.pageSize + 1}-${Math.min(
                  pagination.page * pagination.pageSize,
                  pagination.total
                )} of ${pagination.total}`}
          </p>
          <div className="flex items-center gap-1.5">
            <Button
              size="sm"
              variant="secondary"
              onClick={() => pagination.onPageChange(Math.max(1, pagination.page - 1))}
              disabled={pagination.page <= 1}
            >
              <ChevronLeft className="h-2.5 w-2.5" />
              Prev
            </Button>
            <span className="text-xs font-medium text-neutral-700">
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

