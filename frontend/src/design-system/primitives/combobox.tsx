"use client";

import { Check, ChevronsUpDown } from "lucide-react";
import { createPortal } from "react-dom";
import { type CSSProperties, useEffect, useMemo, useRef, useState } from "react";

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
  actionLabel?: string;
  onAction?: () => void;
  onSearchChange?: (query: string) => void;
  serverSearch?: boolean;
  minSearchChars?: number;
  minSearchText?: string;
  portal?: boolean;
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
  size = "md",
  actionLabel,
  onAction,
  onSearchChange,
  serverSearch = false,
  minSearchChars = 0,
  minSearchText,
  portal = true
}: ComboboxProps): JSX.Element {
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [menuStyle, setMenuStyle] = useState<CSSProperties | null>(null);

  const updateMenuPosition = (): void => {
    const trigger = triggerRef.current;
    if (!trigger) {
      return;
    }

    const rect = trigger.getBoundingClientRect();
    const margin = 8;
    const preferredMaxHeight = 320;
    const spaceBelow = window.innerHeight - rect.bottom - margin;
    const spaceAbove = rect.top - margin;
    const showAbove = spaceBelow < 220 && spaceAbove > spaceBelow;
    const maxHeight = Math.max(140, Math.min(preferredMaxHeight, showAbove ? spaceAbove : spaceBelow));

    setMenuStyle({
      position: "fixed",
      left: rect.left,
      top: showAbove ? Math.max(margin, rect.top - maxHeight - 4) : rect.bottom + 4,
      width: rect.width,
      maxHeight,
      zIndex: 220
    });
  };

  useEffect(() => {
    if (!open) {
      return;
    }

    if (portal) {
      updateMenuPosition();
    }

    const onPointerDown = (event: MouseEvent): void => {
      if (!rootRef.current) {
        return;
      }
      const targetNode = event.target as Node;
      const clickInsideTrigger = rootRef.current.contains(targetNode);
      const clickInsideMenu = menuRef.current?.contains(targetNode) ?? false;

      if (!clickInsideTrigger && !clickInsideMenu) {
        setOpen(false);
      }
    };

    const onEscape = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };

    const onReposition = (): void => {
      if (portal) {
        updateMenuPosition();
      }
    };

    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onEscape);
    window.addEventListener("scroll", onReposition, true);
    window.addEventListener("resize", onReposition);

    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onEscape);
      window.removeEventListener("scroll", onReposition, true);
      window.removeEventListener("resize", onReposition);
    };
  }, [open, portal]);

  useEffect(() => {
    if (!onSearchChange) return;
    const timer = setTimeout(() => onSearchChange(query), 250);
    return () => clearTimeout(timer);
  }, [query, onSearchChange]);

  const selected = useMemo(() => options.find((option) => option.value === value) ?? null, [options, value]);

  const filteredOptions = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (minSearchChars > 0 && normalizedQuery.length < minSearchChars) {
      return [];
    }

    if (serverSearch || !normalizedQuery) {
      return options;
    }

    return options.filter((option) => {
      // Do not search by internal option.value (often UUID) to avoid false-positive matches.
      const haystack = [option.label, ...(option.keywords ?? [])].join(" ").toLowerCase();
      return haystack.includes(normalizedQuery);
    });
  }, [minSearchChars, options, query, serverSearch]);

  const normalizedQuery = query.trim();
  const searchThresholdMet = minSearchChars <= 0 || normalizedQuery.length >= minSearchChars;
  const resolvedEmptyText = !searchThresholdMet ? (minSearchText ?? `Type at least ${minSearchChars} characters`) : emptyText;

  const applyOption = (nextValue: string): void => {
    onChange(nextValue);
    setOpen(false);
    setQuery("");
  };

  return (
    <div className={cn("relative", className)} ref={rootRef}>
      {name ? <input type="hidden" name={name} value={value} /> : null}
      <button
        ref={triggerRef}
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

      {open
        ? portal
          ? menuStyle
            ? createPortal(
                <div
                  data-floating-menu="true"
                  ref={menuRef}
                  className="overflow-hidden rounded-md border border-neutral-200 bg-neutral-0 p-2 shadow-md"
                  style={menuStyle}
                >
                  <Input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder={searchPlaceholder}
                    className={size === "sm" ? "h-8" : "h-9"}
                    autoFocus
                  />
                  <div className="mt-2 max-h-[232px] overflow-auto rounded-md border border-neutral-200 bg-neutral-50 p-1">
                    {filteredOptions.length === 0 ? (
                      <p className="px-2 py-2 text-xs text-neutral-600">{resolvedEmptyText}</p>
                    ) : (
                      filteredOptions.map((option) => (
                        <button
                          type="button"
                          key={option.value}
                          className={cn(
                            "flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-sm",
                            option.value === value ? "bg-primary/10 text-primary" : "text-neutral-800 hover:bg-neutral-100"
                          )}
                          onPointerDown={(event) => {
                            event.preventDefault();
                            event.stopPropagation();
                            applyOption(option.value);
                          }}
                          onClick={(event) => {
                            if (event.detail !== 0) {
                              return;
                            }
                            applyOption(option.value);
                          }}
                        >
                          <span className="truncate pr-2">{option.label}</span>
                          {option.value === value ? <Check className="h-3.5 w-3.5 shrink-0" /> : null}
                        </button>
                      ))
                    )}
                  </div>
                  {actionLabel && onAction ? (
                    <div className="mt-2 border-t border-neutral-200 pt-2">
                      <button
                        type="button"
                        className="w-full rounded-md px-2 py-1.5 text-left text-xs font-semibold text-primary hover:bg-primary/5"
                        onPointerDown={(event) => {
                          event.preventDefault();
                          event.stopPropagation();
                          onAction();
                          setOpen(false);
                          setQuery("");
                        }}
                        onClick={(event) => {
                          if (event.detail !== 0) {
                            return;
                          }
                          onAction();
                          setOpen(false);
                          setQuery("");
                        }}
                      >
                        {actionLabel}
                      </button>
                    </div>
                  ) : null}
                </div>,
                document.body
              )
            : null
          : (
              <div
                data-floating-menu="true"
                ref={menuRef}
                className="absolute left-0 top-[calc(100%+4px)] z-[140] w-full overflow-hidden rounded-md border border-neutral-200 bg-neutral-0 p-2 shadow-md"
              >
                <Input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder={searchPlaceholder}
                  className={size === "sm" ? "h-8" : "h-9"}
                  autoFocus
                />
                <div className="mt-2 max-h-[232px] overflow-auto rounded-md border border-neutral-200 bg-neutral-50 p-1">
                  {filteredOptions.length === 0 ? (
                    <p className="px-2 py-2 text-xs text-neutral-600">{resolvedEmptyText}</p>
                  ) : (
                    filteredOptions.map((option) => (
                      <button
                        type="button"
                        key={option.value}
                        className={cn(
                          "flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-sm",
                          option.value === value ? "bg-primary/10 text-primary" : "text-neutral-800 hover:bg-neutral-100"
                        )}
                        onPointerDown={(event) => {
                          event.preventDefault();
                          event.stopPropagation();
                          applyOption(option.value);
                        }}
                        onClick={(event) => {
                          if (event.detail !== 0) {
                            return;
                          }
                          applyOption(option.value);
                        }}
                      >
                        <span className="truncate pr-2">{option.label}</span>
                        {option.value === value ? <Check className="h-3.5 w-3.5 shrink-0" /> : null}
                      </button>
                    ))
                  )}
                </div>
                {actionLabel && onAction ? (
                  <div className="mt-2 border-t border-neutral-200 pt-2">
                    <button
                      type="button"
                      className="w-full rounded-md px-2 py-1.5 text-left text-xs font-semibold text-primary hover:bg-primary/5"
                      onPointerDown={(event) => {
                        event.preventDefault();
                        event.stopPropagation();
                        onAction();
                        setOpen(false);
                        setQuery("");
                      }}
                      onClick={(event) => {
                        if (event.detail !== 0) {
                          return;
                        }
                        onAction();
                        setOpen(false);
                        setQuery("");
                      }}
                    >
                      {actionLabel}
                    </button>
                  </div>
                ) : null}
              </div>
            )
        : null}
    </div>
  );
}
