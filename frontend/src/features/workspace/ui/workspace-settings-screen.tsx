"use client";

import { ImagePlus, Trash2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";

import { formatPhoneInput, normalizePhoneForSubmit } from "@/core/lib/phone";
import { Badge, Button, Combobox, FormField, Input, PhoneInput, Select, Textarea } from "@/design-system/primitives";
import { PageLayout, StateBoundary } from "@/design-system/patterns";
import {
  fetchWorkspaceContext,
  fetchWorkspaceSettings,
  mvpQueryKeys,
  updateWorkspaceSettings
} from "@/features/workspace/api/mvp-api";
import { getTimezoneOptions } from "@/features/workspace/lib/timezone-options";
import { AddressAutocompleteField, type AddressSuggestionSelection } from "@/features/workspace/ui/address-autocomplete-field";

type SettingsFormState = {
  service_name: string;
  phone: string;
  address: string;
  timezone: string;
  currency: string;
  working_hours_note: string;
};

const TIMEZONE_LOOKUP_API_URL = process.env.NEXT_PUBLIC_TIMEZONE_LOOKUP_URL ?? "https://timeapi.io/api/TimeZone/coordinate";

const COUNTRY_CURRENCY_MAP: Record<string, string> = {
  RU: "RUB",
  KZ: "KZT",
  BY: "BYN",
  UA: "UAH",
  US: "USD",
  CA: "CAD",
  MX: "MXN",
  GB: "GBP",
  TR: "TRY",
  JP: "JPY",
  CN: "CNY",
  KR: "KRW",
  IN: "INR",
  BR: "BRL",
  AE: "AED",
  SA: "SAR",
  EG: "EGP",
  ZA: "ZAR",
  AU: "AUD",
  NZ: "NZD"
};

const EUR_COUNTRY_CODES = new Set([
  "AT",
  "BE",
  "CY",
  "DE",
  "EE",
  "ES",
  "FI",
  "FR",
  "GR",
  "HR",
  "IE",
  "IT",
  "LT",
  "LU",
  "LV",
  "MT",
  "NL",
  "PT",
  "SI",
  "SK"
]);

const COUNTRY_TIMEZONE_FALLBACK: Record<string, string> = {
  RU: "Europe/Moscow",
  US: "America/New_York",
  GB: "Europe/London",
  DE: "Europe/Berlin",
  FR: "Europe/Paris",
  ES: "Europe/Madrid",
  IT: "Europe/Rome",
  PL: "Europe/Warsaw",
  TR: "Europe/Istanbul",
  AE: "Asia/Dubai",
  KZ: "Asia/Almaty",
  IN: "Asia/Kolkata",
  CN: "Asia/Shanghai",
  JP: "Asia/Tokyo",
  KR: "Asia/Seoul",
  AU: "Australia/Sydney"
};

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString();
}

function isValidIanaTimezone(value: string): boolean {
  try {
    new Intl.DateTimeFormat("en-US", { timeZone: value }).format(new Date());
    return true;
  } catch {
    return false;
  }
}

function suggestCurrencyByCountry(countryCode?: string): string | null {
  if (!countryCode) {
    return null;
  }
  if (EUR_COUNTRY_CODES.has(countryCode)) {
    return "EUR";
  }
  return COUNTRY_CURRENCY_MAP[countryCode] ?? null;
}

function fallbackTimezoneByCountry(countryCode?: string): string | null {
  if (!countryCode) {
    return null;
  }
  return COUNTRY_TIMEZONE_FALLBACK[countryCode] ?? null;
}

async function detectTimezoneByCoordinates(latitude: number, longitude: number): Promise<string | null> {
  const params = new URLSearchParams({
    latitude: String(latitude),
    longitude: String(longitude)
  });
  const response = await fetch(`${TIMEZONE_LOOKUP_API_URL}?${params.toString()}`);
  if (!response.ok) {
    return null;
  }

  const payload = (await response.json()) as {
    timeZone?: string;
    timezone?: string;
    ianaTimeZoneId?: string;
  };

  const raw = payload.timeZone ?? payload.timezone ?? payload.ianaTimeZoneId;
  if (!raw) {
    return null;
  }

  return isValidIanaTimezone(raw) ? raw : null;
}

export function WorkspaceSettingsScreen(): JSX.Element {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const timezonePopoverRef = useRef<HTMLDivElement>(null);
  const timezoneOptions = useMemo(() => getTimezoneOptions(), []);

  const contextQuery = useQuery({
    queryKey: mvpQueryKeys.workspaceContext,
    queryFn: fetchWorkspaceContext
  });

  const settingsQuery = useQuery({
    queryKey: mvpQueryKeys.workspaceSettings,
    queryFn: fetchWorkspaceSettings
  });

  const updateMutation = useMutation({
    mutationFn: updateWorkspaceSettings,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workspaceSettings });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workspaceContext });
    }
  });

  const [form, setForm] = useState<SettingsFormState>({
    service_name: "",
    phone: "",
    address: "",
    timezone: "UTC",
    currency: "USD",
    working_hours_note: ""
  });
  const [formError, setFormError] = useState<string | null>(null);
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [logoPreviewUrl, setLogoPreviewUrl] = useState<string | null>(null);
  const [logoNotice, setLogoNotice] = useState<string | null>(null);
  const [timezoneManualOverride, setTimezoneManualOverride] = useState(false);
  const [timezoneHelperText, setTimezoneHelperText] = useState("Detected from selected address.");
  const [detectedTimezone, setDetectedTimezone] = useState<string | null>(null);
  const [timezonePickerOpen, setTimezonePickerOpen] = useState(false);
  const [timezoneDraft, setTimezoneDraft] = useState("UTC");
  const [currencySuggestion, setCurrencySuggestion] = useState<string | null>(null);
  const [currencySuggestionSource, setCurrencySuggestionSource] = useState<string | null>(null);
  const [currencyManuallyChanged, setCurrencyManuallyChanged] = useState(false);

  useEffect(() => {
    if (!settingsQuery.data) {
      return;
    }
    setForm({
      service_name: settingsQuery.data.service_name,
      phone: formatPhoneInput(settingsQuery.data.phone),
      address: settingsQuery.data.address ?? "",
      timezone: settingsQuery.data.timezone,
      currency: settingsQuery.data.currency,
      working_hours_note: settingsQuery.data.working_hours_note ?? ""
    });
    setTimezoneManualOverride(false);
    setTimezoneHelperText("Detected from selected address.");
    setDetectedTimezone(settingsQuery.data.timezone);
    setTimezoneDraft(settingsQuery.data.timezone);
    setTimezonePickerOpen(false);
    setCurrencySuggestion(null);
    setCurrencySuggestionSource(null);
    setCurrencyManuallyChanged(false);
  }, [settingsQuery.data]);

  useEffect(() => {
    if (!logoFile) {
      setLogoPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(logoFile);
    setLogoPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [logoFile]);

  useEffect(() => {
    if (!timezonePickerOpen) {
      return;
    }

    const onPointerDown = (event: MouseEvent): void => {
      if (!timezonePopoverRef.current) {
        return;
      }
      if (!timezonePopoverRef.current.contains(event.target as Node)) {
        setTimezonePickerOpen(false);
      }
    };

    const onEscape = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        setTimezonePickerOpen(false);
      }
    };

    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onEscape);

    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onEscape);
    };
  }, [timezonePickerOpen]);

  const mergedTimezoneOptions = useMemo(() => {
    if (!form.timezone || timezoneOptions.some((option) => option.value === form.timezone)) {
      return timezoneOptions;
    }

    if (!isValidIanaTimezone(form.timezone)) {
      return timezoneOptions;
    }

    return [
      ...timezoneOptions,
      {
        value: form.timezone,
        label: form.timezone,
        keywords: [form.timezone]
      }
    ];
  }, [form.timezone, timezoneOptions]);

  const timezoneExists = mergedTimezoneOptions.some((option) => option.value === form.timezone);

  const onAddressSuggestionSelect = async (selection: AddressSuggestionSelection): Promise<void> => {
    const countryCode = selection.countryCode?.toUpperCase();

    const nextCurrencySuggestion = suggestCurrencyByCountry(countryCode);
    if (nextCurrencySuggestion) {
      setCurrencySuggestion(nextCurrencySuggestion);
      setCurrencySuggestionSource(countryCode ?? "address");
      if (!currencyManuallyChanged) {
        setForm((prev) => ({ ...prev, currency: nextCurrencySuggestion }));
      }
    } else {
      setCurrencySuggestion(null);
      setCurrencySuggestionSource(null);
    }

    if (selection.latitude == null || selection.longitude == null) {
      const timezoneFromCountry = fallbackTimezoneByCountry(countryCode);
      if (timezoneFromCountry) {
        setDetectedTimezone(timezoneFromCountry);
        setTimezoneHelperText("Estimated from selected country.");
        if (!timezoneManualOverride) {
          setForm((prev) => ({ ...prev, timezone: timezoneFromCountry }));
        }
      } else {
        setTimezoneHelperText("Could not detect timezone automatically. Change manually if needed.");
      }
      return;
    }

    setTimezoneHelperText("Detecting timezone from selected address...");

    try {
      const timezoneByCoordinates = await detectTimezoneByCoordinates(selection.latitude, selection.longitude);

      if (timezoneByCoordinates) {
        setDetectedTimezone(timezoneByCoordinates);
        setTimezoneHelperText("Detected from selected address.");
        if (!timezoneManualOverride) {
          setForm((prev) => ({ ...prev, timezone: timezoneByCoordinates }));
        }
        return;
      }

      const timezoneFromCountry = fallbackTimezoneByCountry(countryCode);
      if (timezoneFromCountry) {
        setDetectedTimezone(timezoneFromCountry);
        setTimezoneHelperText("Timezone service unavailable. Estimated from selected country.");
        if (!timezoneManualOverride) {
          setForm((prev) => ({ ...prev, timezone: timezoneFromCountry }));
        }
        return;
      }

      setTimezoneHelperText("Could not detect timezone automatically. Change manually if needed.");
    } catch {
      const timezoneFromCountry = fallbackTimezoneByCountry(countryCode);
      if (timezoneFromCountry) {
        setDetectedTimezone(timezoneFromCountry);
        setTimezoneHelperText("Timezone lookup failed. Estimated from selected country.");
        if (!timezoneManualOverride) {
          setForm((prev) => ({ ...prev, timezone: timezoneFromCountry }));
        }
        return;
      }

      setTimezoneHelperText("Could not detect timezone automatically. Change manually if needed.");
    }
  };

  return (
    <PageLayout
      title="Workspace settings"
      subtitle={contextQuery.data ? `${contextQuery.data.workspace_name} (${contextQuery.data.workspace_slug})` : "Workspace"}
    >
      <StateBoundary
        loading={settingsQuery.isLoading || contextQuery.isLoading}
        error={settingsQuery.error?.message ?? contextQuery.error?.message}
      >
        {settingsQuery.data ? (
          <form
            className="rounded-lg border border-neutral-300 bg-neutral-0 shadow-sm"
            onSubmit={(event) => {
              event.preventDefault();
              setFormError(null);
              setLogoNotice(null);

              if (!form.service_name.trim() || !form.phone.trim()) {
                setFormError("Service name and phone are required.");
                return;
              }
              if (!timezoneExists) {
                setFormError("Timezone value is not valid.");
                return;
              }
              if (!form.currency.trim()) {
                setFormError("Currency is required.");
                return;
              }

              void updateMutation.mutateAsync(
                {
                  service_name: form.service_name.trim(),
                  phone: normalizePhoneForSubmit(form.phone),
                  address: form.address.trim() || null,
                  timezone: form.timezone,
                  currency: form.currency.trim().toUpperCase(),
                  working_hours_note: form.working_hours_note.trim() || null
                },
                {
                  onSuccess: () => {
                    if (logoFile) {
                      setLogoNotice("Logo selected locally. Backend upload endpoint is required to persist logo.");
                    }
                  }
                }
              );
            }}
          >
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-200 bg-neutral-50 px-4 py-3">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Configuration center</p>
                <p className="mt-1 text-sm text-neutral-700">Workspace profile, regional defaults and operator notes.</p>
              </div>
              <p className="text-xs text-neutral-600">Updated {formatDateTime(settingsQuery.data.updated_at)}</p>
            </div>

            <div className="mx-auto w-full max-w-[920px] space-y-4 p-4">
              <section className="space-y-3 rounded-md border border-neutral-200 p-4">
                <div>
                  <h2 className="text-[16px] font-semibold text-neutral-900">Business profile</h2>
                  <p className="mt-1 text-sm text-neutral-600">Core contact identity shown in operational screens and documents.</p>
                </div>

                <div className="rounded-md border border-neutral-200 bg-neutral-50 p-3">
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="h-[56px] w-[56px] overflow-hidden rounded-md border border-neutral-200 bg-neutral-0">
                      {logoPreviewUrl ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={logoPreviewUrl} alt="Workspace logo preview" className="h-full w-full object-cover" />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center text-xs font-medium text-neutral-500">No logo</div>
                      )}
                    </div>

                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-neutral-800">Workspace logo</p>
                      <p className="text-xs text-neutral-600">PNG, JPG or SVG. Recommended square image.</p>
                    </div>

                    <div className="flex items-center gap-2">
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/png,image/jpeg,image/svg+xml"
                        className="hidden"
                        onChange={(event) => {
                          const file = event.target.files?.[0] ?? null;
                          setLogoFile(file);
                          setLogoNotice(null);
                        }}
                      />
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => {
                          fileInputRef.current?.click();
                        }}
                      >
                        <ImagePlus className="h-4 w-4" />
                        {logoFile ? "Replace" : "Upload"}
                      </Button>
                      {logoFile ? (
                        <Button
                          type="button"
                          variant="ghost"
                          onClick={() => {
                            setLogoFile(null);
                            if (fileInputRef.current) {
                              fileInputRef.current.value = "";
                            }
                          }}
                        >
                          <Trash2 className="h-4 w-4" />
                          Remove
                        </Button>
                      ) : null}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  <FormField id="service_name" label="Service name" required>
                    <Input
                      id="service_name"
                      className="h-[36px]"
                      value={form.service_name}
                      onChange={(event) => setForm((prev) => ({ ...prev, service_name: event.target.value }))}
                    />
                  </FormField>
                  <FormField id="phone" label="Phone" required hint="Primary service desk contact">
                    <PhoneInput
                      id="phone"
                      className="h-[36px]"
                      value={form.phone}
                      onChange={(phone) => setForm((prev) => ({ ...prev, phone }))}
                    />
                  </FormField>
                </div>

                <div className="space-y-3 rounded-md border border-neutral-200 bg-neutral-50 p-3">
                  <div>
                    <h3 className="text-sm font-semibold text-neutral-900">Location and regional defaults</h3>
                    <p className="mt-1 text-xs text-neutral-600">Address drives timezone detection. Currency stays configurable.</p>
                  </div>

                  <FormField
                    id="address"
                    label="Address"
                    hint="Search and select online. Russian input returns Russian suggestions, English input returns English suggestions."
                  >
                    <div className="space-y-2">
                      <AddressAutocompleteField
                        id="address"
                        name="address"
                        value={form.address}
                        onChange={(address) => setForm((prev) => ({ ...prev, address }))}
                        onSuggestionSelect={(selection) => void onAddressSuggestionSelect(selection)}
                      />

                      <div className="relative" ref={timezonePopoverRef}>
                        <div className="flex flex-wrap items-center gap-2 text-xs">
                          <span className="text-neutral-500">Timezone:</span>
                          <button
                            type="button"
                            className="rounded-sm border border-neutral-200 bg-neutral-0 px-2 py-1 font-medium text-neutral-800 hover:border-neutral-300"
                            onClick={() => {
                              setTimezoneDraft(form.timezone);
                              setTimezonePickerOpen(true);
                            }}
                          >
                            {form.timezone}
                          </button>
                          {timezoneManualOverride ? <Badge tone="neutral">Manual</Badge> : null}
                          {timezoneManualOverride && detectedTimezone ? (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setTimezoneManualOverride(false);
                                setForm((prev) => ({ ...prev, timezone: detectedTimezone }));
                                setTimezonePickerOpen(false);
                              }}
                            >
                              Use auto-detected timezone
                            </Button>
                          ) : null}
                        </div>
                        <p className="mt-1 text-xs text-neutral-600">
                          {timezoneManualOverride ? "Manual override enabled." : timezoneHelperText}
                        </p>

                        {timezonePickerOpen ? (
                          <div className="absolute left-0 top-[calc(100%+8px)] z-30 w-full rounded-md border border-neutral-200 bg-neutral-0 p-2 shadow-md">
                            <Combobox
                              id="timezone-manual-override"
                              name="timezone-manual-override"
                              value={timezoneDraft}
                              onChange={setTimezoneDraft}
                              options={mergedTimezoneOptions}
                              placeholder="Select timezone"
                              searchPlaceholder="Search timezone..."
                            />
                            <div className="mt-2 flex items-center justify-end gap-2">
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setTimezonePickerOpen(false);
                                  setTimezoneDraft(form.timezone);
                                }}
                              >
                                Cancel
                              </Button>
                              <Button
                                type="button"
                                variant="secondary"
                                size="sm"
                                onClick={() => {
                                  setForm((prev) => ({ ...prev, timezone: timezoneDraft }));
                                  setTimezoneManualOverride(true);
                                  setTimezonePickerOpen(false);
                                }}
                              >
                                Apply
                              </Button>
                            </div>
                          </div>
                        ) : null}
                      </div>
                    </div>
                  </FormField>

                  <FormField id="currency" label="Currency" required hint="ISO code. Auto-suggested from selected address country when available.">
                    <div className="space-y-2">
                      <Select
                        id="currency"
                        className="h-[36px]"
                        value={form.currency}
                        onChange={(event) => {
                          const nextCurrency = event.target.value;
                          setCurrencyManuallyChanged(true);
                          setForm((prev) => ({ ...prev, currency: nextCurrency }));
                        }}
                      >
                        <option value="USD">USD</option>
                        <option value="EUR">EUR</option>
                        <option value="RUB">RUB</option>
                        <option value="GBP">GBP</option>
                        <option value="KZT">KZT</option>
                      </Select>
                      {currencySuggestion ? (
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge tone="neutral">
                            Suggested: {currencySuggestion}
                            {currencySuggestionSource ? ` (${currencySuggestionSource})` : ""}
                          </Badge>
                          {currencySuggestion !== form.currency ? (
                            <Button
                              type="button"
                              variant="ghost"
                              onClick={() => {
                                setCurrencyManuallyChanged(false);
                                setForm((prev) => ({ ...prev, currency: currencySuggestion }));
                              }}
                            >
                              Apply suggestion
                            </Button>
                          ) : null}
                        </div>
                      ) : null}
                    </div>
                  </FormField>
                </div>
              </section>

              <section className="space-y-3 rounded-md border border-neutral-200 p-4">
                <div>
                  <h2 className="text-[16px] font-semibold text-neutral-900">Operational notes</h2>
                  <p className="mt-1 text-sm text-neutral-600">Short note for business hours, handover rules, or service desk specifics.</p>
                </div>
                <FormField id="working_hours_note" label="Working hours note">
                  <Textarea
                    id="working_hours_note"
                    className="min-h-28"
                    value={form.working_hours_note}
                    onChange={(event) => setForm((prev) => ({ ...prev, working_hours_note: event.target.value }))}
                  />
                </FormField>
              </section>
            </div>

            {formError ? <p className="px-4 pb-2 text-sm text-error">{formError}</p> : null}
            {updateMutation.error ? <p className="px-4 pb-2 text-sm text-error">{updateMutation.error.message}</p> : null}
            {logoNotice ? (
              <div className="px-4 pb-2">
                <Badge tone="warning">{logoNotice}</Badge>
              </div>
            ) : null}

            <div className="sticky bottom-0 border-t border-neutral-200 bg-neutral-50 px-4 py-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs text-neutral-600">Changes apply to this workspace immediately after save.</p>
                <Button type="submit" variant="primary" loading={updateMutation.isPending}>
                  Save workspace settings
                </Button>
              </div>
            </div>
          </form>
        ) : null}
      </StateBoundary>
    </PageLayout>
  );
}
