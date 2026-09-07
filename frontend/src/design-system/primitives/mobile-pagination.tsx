"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/design-system/primitives/button";

type MobilePaginationProps = {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  label: string;
  prevLabel: string;
  nextLabel: string;
};

export function MobilePagination({
  page,
  pageSize,
  total,
  onPageChange,
  label,
  prevLabel,
  nextLabel
}: MobilePaginationProps): JSX.Element | null {
  if (total <= 0) {
    return null;
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="flex items-center justify-between gap-2 rounded-md border border-neutral-200 bg-neutral-0 px-2.5 py-2 md:hidden">
      <Button
        type="button"
        size="sm"
        variant="secondary"
        className="h-9 min-w-[44px] px-2"
        onClick={() => onPageChange(Math.max(1, page - 1))}
        disabled={page <= 1}
        aria-label={prevLabel}
      >
        <ChevronLeft className="h-4 w-4" />
      </Button>
      <span className="text-xs font-semibold text-neutral-700">{label.replace("{page}", String(page)).replace("{total}", String(totalPages))}</span>
      <Button
        type="button"
        size="sm"
        variant="secondary"
        className="h-9 min-w-[44px] px-2"
        onClick={() => onPageChange(Math.min(totalPages, page + 1))}
        disabled={page >= totalPages}
        aria-label={nextLabel}
      >
        <ChevronRight className="h-4 w-4" />
      </Button>
    </div>
  );
}

