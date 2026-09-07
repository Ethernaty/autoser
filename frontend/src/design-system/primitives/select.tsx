"use client";

import * as React from "react";
import { createPortal } from "react-dom";
import { ChevronDown } from "lucide-react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/core/lib/utils";

const selectVariants = cva(
  "w-full rounded-md border px-3 pr-8 text-sm text-neutral-900 shadow-[inset_0_1px_1px_rgba(15,23,42,0.04)] outline-none transition-colors duration-150 ease-standard focus-visible:ring-2 focus-visible:ring-primary/35 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "border-neutral-300 bg-neutral-0",
        subtle: "border-neutral-200 bg-neutral-50"
      },
      invalid: {
        true: "border-error focus-visible:ring-error/35",
        false: ""
      },
      size: {
        sm: "h-8",
        md: "h-9"
      }
    },
    defaultVariants: {
      variant: "default",
      invalid: false,
      size: "md"
    }
  }
);

type ParsedOption = {
  value: string;
  label: string;
  disabled?: boolean;
};

function parseOptions(children: React.ReactNode): ParsedOption[] {
  const options: ParsedOption[] = [];

  React.Children.forEach(children, (child) => {
    if (!React.isValidElement(child)) {
      return;
    }
    if (typeof child.type !== "string" || child.type !== "option") {
      return;
    }

    const rawValue = child.props.value;
    const value = rawValue == null ? "" : String(rawValue);
    const label = React.Children.toArray(child.props.children).join("") || value;

    options.push({
      value,
      label,
      disabled: Boolean(child.props.disabled)
    });
  });

  return options;
}

export type SelectProps = VariantProps<typeof selectVariants> & {
  id?: string;
  name?: string;
  value?: string | number;
  defaultValue?: string | number;
  triggerLabel?: string;
  portal?: boolean;
  disabled?: boolean;
  required?: boolean;
  className?: string;
  title?: string;
  "aria-label"?: string;
  children?: React.ReactNode;
  onChange?: (event: React.ChangeEvent<HTMLSelectElement>) => void;
};

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  (
    {
      className,
      variant,
      invalid,
      size,
      children,
      value,
      defaultValue,
      triggerLabel,
      name,
      onChange,
      disabled,
      id,
      title,
      required,
      portal = true,
      ...props
    },
    ref
  ) => {
    const rootRef = React.useRef<HTMLDivElement>(null);
    const buttonRef = React.useRef<HTMLButtonElement>(null);
    const menuRef = React.useRef<HTMLDivElement>(null);
    const [open, setOpen] = React.useState(false);
    const [menuStyle, setMenuStyle] = React.useState<React.CSSProperties | null>(null);

    const options = React.useMemo(() => parseOptions(children), [children]);
    const isControlled = value !== undefined;
    const initialValue = React.useMemo(() => {
      const nextDefault = defaultValue == null ? "" : String(defaultValue);
      if (nextDefault) {
        return nextDefault;
      }
      if (options.some((option) => option.value === "")) {
        return "";
      }
      return options[0]?.value ?? "";
    }, [defaultValue, options]);

    const [internalValue, setInternalValue] = React.useState(initialValue);
    const selectedValue = isControlled ? (value == null ? "" : String(value)) : internalValue;

    React.useEffect(() => {
      if (!isControlled) {
        setInternalValue(initialValue);
      }
    }, [initialValue, isControlled]);

    const selectedOption =
      options.find((option) => option.value === selectedValue) ??
      options.find((option) => option.value === "") ??
      options[0] ??
      null;

    const updateMenuPosition = React.useCallback(() => {
      const trigger = buttonRef.current;
      if (!trigger) {
        return;
      }

      const rect = trigger.getBoundingClientRect();
      const margin = 8;
      const preferredMaxHeight = 280;
      const spaceBelow = window.innerHeight - rect.bottom - margin;
      const spaceAbove = rect.top - margin;
      const showAbove = spaceBelow < 180 && spaceAbove > spaceBelow;
      const maxHeight = Math.max(120, Math.min(preferredMaxHeight, showAbove ? spaceAbove : spaceBelow));

      setMenuStyle({
        position: "fixed",
        left: rect.left,
        top: showAbove ? Math.max(margin, rect.top - maxHeight - 4) : rect.bottom + 4,
        width: rect.width,
        maxHeight,
        zIndex: 220
      });
    }, []);

    React.useEffect(() => {
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
    }, [open, portal, updateMenuPosition]);

    const emitChange = (nextValue: string): void => {
      if (!isControlled) {
        setInternalValue(nextValue);
      }

      if (!onChange) {
        return;
      }

      const syntheticEvent = {
        target: {
          value: nextValue,
          name
        }
      } as unknown as React.ChangeEvent<HTMLSelectElement>;

      onChange(syntheticEvent);
    };

    const applyOption = (nextValue: string): void => {
      emitChange(nextValue);
      setOpen(false);
    };

    return (
      <div className="relative min-w-0 w-full" ref={rootRef}>
        <select
          ref={ref}
          name={name}
          value={selectedValue}
          required={required}
          onChange={(event) => emitChange(event.target.value)}
          className="pointer-events-none absolute h-0 w-0 opacity-0"
          tabIndex={-1}
          aria-hidden="true"
        >
          {options.map((option) => (
            <option key={`${name ?? "hidden"}-${option.value}`} value={option.value} disabled={option.disabled}>
              {option.label}
            </option>
          ))}
        </select>

        <button
          ref={buttonRef}
          type="button"
          id={id}
          title={title}
          className={cn(
            "flex min-w-0 max-w-full w-full items-center justify-between gap-2 text-left",
            selectVariants({ variant, invalid, size }),
            className
          )}
          aria-label={props["aria-label"]}
          aria-expanded={open}
          aria-haspopup="listbox"
          disabled={disabled}
          onClick={() => setOpen((prev) => !prev)}
        >
          <span className={cn("min-w-0 truncate", selectedOption ? "text-neutral-900" : "text-neutral-500")}>
            {triggerLabel ?? selectedOption?.label ?? ""}
          </span>
          <ChevronDown className="h-3.5 w-3.5 shrink-0 text-neutral-500" />
        </button>

        {open && (portal ? menuStyle : true)
          ? portal
            ? createPortal(
              <div
                data-floating-menu="true"
                ref={menuRef}
                className="overflow-auto rounded-md border border-neutral-200 bg-neutral-0 p-1 shadow-md"
                style={menuStyle ?? undefined}
                role="listbox"
              >
                {options.map((option) => (
                  <button
                    key={`${name ?? "select"}-${option.value}`}
                    type="button"
                    className={cn(
                      "w-full rounded-md px-2 py-1.5 text-left text-sm transition-colors",
                      option.value === selectedValue ? "bg-primary/10 text-primary" : "text-neutral-800 hover:bg-neutral-100",
                      option.disabled && "pointer-events-none opacity-50"
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
                    disabled={option.disabled}
                  >
                    {option.label}
                  </button>
                ))}
              </div>,
              document.body
            )
            : (
              <div
                data-floating-menu="true"
                ref={menuRef}
                className="absolute left-0 top-[calc(100%+4px)] z-[140] max-h-[280px] w-full overflow-auto rounded-md border border-neutral-200 bg-neutral-0 p-1 shadow-md"
                role="listbox"
              >
                {options.map((option) => (
                  <button
                    key={`${name ?? "select"}-${option.value}`}
                    type="button"
                    className={cn(
                      "w-full rounded-md px-2 py-1.5 text-left text-sm transition-colors",
                      option.value === selectedValue ? "bg-primary/10 text-primary" : "text-neutral-800 hover:bg-neutral-100",
                      option.disabled && "pointer-events-none opacity-50"
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
                    disabled={option.disabled}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            )
          : null}
      </div>
    );
  }
);

Select.displayName = "Select";
