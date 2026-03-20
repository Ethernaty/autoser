"use client";

import { Loader2, MapPin } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { cn } from "@/core/lib/utils";
import { Input } from "@/design-system/primitives/input";

type AddressSuggestion = {
  label: string;
  secondary?: string;
  latitude: number | null;
  longitude: number | null;
  countryCode?: string;
  language: "ru" | "en";
};

export type AddressSuggestionSelection = {
  label: string;
  latitude: number | null;
  longitude: number | null;
  countryCode?: string;
  language: "ru" | "en";
};

type AddressAutocompleteFieldProps = {
  id: string;
  name?: string;
  value: string;
  onChange: (value: string) => void;
  onSuggestionSelect?: (selection: AddressSuggestionSelection) => void | Promise<void>;
  className?: string;
};

const ADDRESS_API_URL = process.env.NEXT_PUBLIC_ADDRESS_AUTOCOMPLETE_URL ?? "https://nominatim.openstreetmap.org/search";

function detectInputLanguage(value: string): "ru" | "en" {
  return /[А-Яа-яЁё]/.test(value) ? "ru" : "en";
}

export function AddressAutocompleteField({
  id,
  name,
  value,
  onChange,
  onSuggestionSelect,
  className
}: AddressAutocompleteFieldProps): JSX.Element {
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<AddressSuggestion[]>([]);

  useEffect(() => {
    const onPointerDown = (event: MouseEvent): void => {
      if (!rootRef.current) {
        return;
      }
      if (!rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    document.addEventListener("mousedown", onPointerDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
    };
  }, []);

  useEffect(() => {
    const normalized = value.trim();
    if (normalized.length < 3) {
      setSuggestions([]);
      setError(null);
      return;
    }

    const controller = new AbortController();
    const timeout = window.setTimeout(async () => {
      const language = detectInputLanguage(normalized);
      setLoading(true);
      setError(null);
      try {
        const search = new URLSearchParams({
          q: normalized,
          format: "jsonv2",
          addressdetails: "1",
          "accept-language": language,
          limit: "6"
        });
        const response = await fetch(`${ADDRESS_API_URL}?${search.toString()}`, {
          signal: controller.signal,
          headers: {
            "Accept-Language": language
          }
        });

        if (!response.ok) {
          throw new Error(`Address service returned ${response.status}`);
        }

        const payload = (await response.json()) as Array<{
          display_name: string;
          name?: string;
          type?: string;
          lat?: string;
          lon?: string;
          address?: {
            country_code?: string;
          };
        }>;

        setSuggestions(
          payload.map((item) => ({
            label: item.display_name,
            secondary: item.name ?? item.type,
            latitude: item.lat ? Number(item.lat) : null,
            longitude: item.lon ? Number(item.lon) : null,
            countryCode: item.address?.country_code?.toUpperCase(),
            language
          }))
        );
        setOpen(true);
      } catch (fetchError) {
        if (controller.signal.aborted) {
          return;
        }
        setSuggestions([]);
        setError(fetchError instanceof Error ? fetchError.message : "Address lookup failed");
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => {
      controller.abort();
      window.clearTimeout(timeout);
    };
  }, [value]);

  const showPanel = useMemo(() => {
    return open && (loading || suggestions.length > 0 || error);
  }, [error, loading, open, suggestions.length]);

  return (
    <div className={cn("relative", className)} ref={rootRef}>
      <Input
        id={id}
        name={name}
        value={value}
        className="h-[36px]"
        onChange={(event) => {
          onChange(event.target.value);
          setOpen(true);
        }}
        placeholder="Search and select address"
      />

      {showPanel ? (
        <div className="absolute left-0 right-0 top-[calc(100%+4px)] z-30 rounded-md border border-neutral-200 bg-neutral-0 p-1 shadow-md">
          {loading ? (
            <div className="flex items-center gap-2 px-2 py-2 text-xs text-neutral-600">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Searching address suggestions...
            </div>
          ) : null}

          {!loading && error ? <p className="px-2 py-2 text-xs text-error">Address lookup unavailable: {error}</p> : null}

          {!loading && !error && suggestions.length === 0 ? (
            <p className="px-2 py-2 text-xs text-neutral-600">No suggestions found. You can keep manual address text.</p>
          ) : null}

          {!loading && !error
            ? suggestions.map((item) => (
                <button
                  type="button"
                  key={item.label}
                  className="flex w-full items-start gap-2 rounded-md px-2 py-1.5 text-left hover:bg-neutral-100"
                  onClick={() => {
                    onChange(item.label);
                    void onSuggestionSelect?.({
                      label: item.label,
                      latitude: Number.isFinite(item.latitude) ? item.latitude : null,
                      longitude: Number.isFinite(item.longitude) ? item.longitude : null,
                      countryCode: item.countryCode,
                      language: item.language
                    });
                    setOpen(false);
                  }}
                >
                  <MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0 text-neutral-500" />
                  <span className="min-w-0">
                    <span className="block truncate text-sm text-neutral-800">{item.label}</span>
                    {item.secondary ? <span className="block truncate text-xs text-neutral-600">{item.secondary}</span> : null}
                  </span>
                </button>
              ))
            : null}
        </div>
      ) : null}
    </div>
  );
}
