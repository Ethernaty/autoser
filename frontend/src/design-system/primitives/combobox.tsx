"use client";

import { Check, ChevronsUpDown } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { cn } from "@/core/lib/utils";
import { Input } from "@/design-system/primitives/input";

export type ComboboxOption = {
  value: string;
  label: string;
  keywords?: string[];
};

type ComboboxProps = {
  id: string;
  value: string;
  onChange: (value: string) => void;
  options: ComboboxOption[];
  placeholder?: string;
  searchPlaceholder?: string;
  emptyText?: string;
  disabled?: boolean;
  className?: string;
  name?: string;
  size?: "sm" | "md";
};

export function Combobox({
  id,
  value,
  onChange,
  options,
  placeholder = "Select option",
  searchPlaceholder = "Search",
  emptyText = "No options found",
  disabled = false,
  className,
  name,
  size = "md"
}: ComboboxProps): JSX.Element {
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    const onPointerDown = (event: MouseEvent): void => {
      if (!rootRef.current) {
        return;
      }
      if (!rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    const onEscape = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };

    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onEscape);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onEscape);
    };
  }, []);

  const selected = useMemo(() => options.find((option) => option.value === value) ?? null, [options, value]);

  const filteredOptions = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) {
      return options;
    }

    return options.filter((option) => {
      const haystack = [option.label, option.value, ...(option.keywords ?? [])].join(" ").toLowerCase();
      return haystack.includes(normalizedQuery);
    });
  }, [options, query]);

  return (
    <div className={cn("relative", className)} ref={rootRef}>
      {name ? <input type="hidden" name={name} value={value} /> : null}
      <button
        type="button"
        id={id}
        onClick={() => !disabled && setOpen((current) => !current)}
        disabled={disabled}
        className={cn(
          "flex w-full items-center justify-between rounded-md border border-neutral-300 bg-neutral-0 px-3 text-left text-sm text-neutral-900",
          size === "sm" ? "h-8" : "h-9",
          "transition-colors hover:border-neutral-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/35",
          "disabled:pointer-events-none disabled:opacity-50"
        )}
      >
        <span className={cn("truncate", selected ? "text-neutral-900" : "text-neutral-500")}>{selected?.label ?? placeholder}</span>
        <ChevronsUpDown className="h-4 w-4 shrink-0 text-neutral-500" />
      </button>

      {open ? (
        <div className="absolute left-0 right-0 top-[calc(100%+4px)] z-30 rounded-md border border-neutral-200 bg-neutral-0 p-2 shadow-md">
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={searchPlaceholder}
            className={size === "sm" ? "h-8" : "h-9"}
            autoFocus
          />
          <div className="mt-2 max-h-[232px] overflow-auto rounded-md border border-neutral-200 bg-neutral-50 p-1">
            {filteredOptions.length === 0 ? (
              <p className="px-2 py-2 text-xs text-neutral-600">{emptyText}</p>
            ) : (
              filteredOptions.map((option) => (
                <button
                  type="button"
                  key={option.value}
                  className={cn(
                    "flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-sm",
                    option.value === value ? "bg-primary/10 text-primary" : "text-neutral-800 hover:bg-neutral-100"
                  )}
                  onClick={() => {
                    onChange(option.value);
                    setOpen(false);
                    setQuery("");
                  }}
                >
                  <span className="truncate pr-2">{option.label}</span>
                  {option.value === value ? <Check className="h-3.5 w-3.5 shrink-0" /> : null}
                </button>
              ))
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
