"use client";

import { ImageOff, ImagePlus, Moon, Sun, Trash2 } from "lucide-react";
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
import { useI18n } from "@/shared/i18n";
import { useTheme } from "@/shared/theme/theme-provider";

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
  const { locale, setLocale, t } = useI18n();
  const { theme, setTheme } = useTheme();
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
  const [timezoneHelperText, setTimezoneHelperText] = useState("");
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
    setTimezoneHelperText(t("settings.timezone.detected"));
    setDetectedTimezone(settingsQuery.data.timezone);
    setTimezoneDraft(settingsQuery.data.timezone);
    setTimezonePickerOpen(false);
    setCurrencySuggestion(null);
    setCurrencySuggestionSource(null);
    setCurrencyManuallyChanged(false);
    setLogoFile(null);
    setLogoPreviewUrl(settingsQuery.data.logo_data_url);
  }, [settingsQuery.data]);

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
        setTimezoneHelperText(t("settings.timezone.estimated_country"));
        if (!timezoneManualOverride) {
          setForm((prev) => ({ ...prev, timezone: timezoneFromCountry }));
        }
      } else {
        setTimezoneHelperText(t("settings.timezone.not_detected"));
      }
      return;
    }

    setTimezoneHelperText(t("settings.timezone.detecting"));

    try {
      const timezoneByCoordinates = await detectTimezoneByCoordinates(selection.latitude, selection.longitude);

      if (timezoneByCoordinates) {
        setDetectedTimezone(timezoneByCoordinates);
        setTimezoneHelperText(t("settings.timezone.detected"));
        if (!timezoneManualOverride) {
          setForm((prev) => ({ ...prev, timezone: timezoneByCoordinates }));
        }
        return;
      }

      const timezoneFromCountry = fallbackTimezoneByCountry(countryCode);
      if (timezoneFromCountry) {
        setDetectedTimezone(timezoneFromCountry);
        setTimezoneHelperText(t("settings.timezone.estimated_service_unavailable"));
        if (!timezoneManualOverride) {
          setForm((prev) => ({ ...prev, timezone: timezoneFromCountry }));
        }
        return;
      }

      setTimezoneHelperText(t("settings.timezone.not_detected"));
    } catch {
      const timezoneFromCountry = fallbackTimezoneByCountry(countryCode);
      if (timezoneFromCountry) {
        setDetectedTimezone(timezoneFromCountry);
        setTimezoneHelperText(t("settings.timezone.estimated_lookup_failed"));
        if (!timezoneManualOverride) {
          setForm((prev) => ({ ...prev, timezone: timezoneFromCountry }));
        }
        return;
      }

      setTimezoneHelperText(t("settings.timezone.not_detected"));
    }
  };

  return (
    <PageLayout
      title={t("settings.title")}
      subtitle={contextQuery.data ? `${contextQuery.data.workspace_name} (${contextQuery.data.workspace_slug})` : t("profile.workspace")}
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
                setFormError(t("settings.error.required_service_phone"));
                return;
              }
              if (!timezoneExists) {
                setFormError(t("settings.error.invalid_timezone"));
                return;
              }
              if (!form.currency.trim()) {
                setFormError(t("settings.error.required_currency"));
                return;
              }

              void updateMutation.mutateAsync(
                {
                  service_name: form.service_name.trim(),
                  phone: normalizePhoneForSubmit(form.phone),
                  address: form.address.trim() || null,
                  timezone: form.timezone,
                  currency: form.currency.trim().toUpperCase(),
                  working_hours_note: form.working_hours_note.trim() || null,
                  logo_data_url: logoPreviewUrl ?? ""
                }
              );
            }}
          >
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-200 bg-neutral-50 px-4 py-3">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wide text-neutral-500">{t("settings.center_label")}</p>
                <p className="mt-1 text-sm text-neutral-700">{t("settings.center_description")}</p>
              </div>
              <p className="text-xs text-neutral-600">
                {t("settings.updated_at", { value: formatDateTime(settingsQuery.data.updated_at) })}
              </p>
            </div>

            <div className="mx-auto w-full max-w-[920px] space-y-4 p-4">
              <section className="space-y-3 rounded-md border border-neutral-200 p-4">
                <div>
                  <h2 className="text-[16px] font-semibold text-neutral-900">{t("settings.business.title")}</h2>
                  <p className="mt-1 text-sm text-neutral-600">{t("settings.business.description")}</p>
                </div>

                <div className="rounded-md border border-neutral-200 bg-neutral-50 p-3">
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="h-[64px] w-[64px] overflow-hidden rounded-md border border-neutral-200 bg-neutral-0">
                      {logoPreviewUrl ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={logoPreviewUrl} alt={t("settings.logo.alt")} className="h-full w-full object-cover" />
                      ) : (
                        <div className="flex h-full w-full flex-col items-center justify-center gap-1 text-neutral-500">
                          <ImageOff className="h-4 w-4" />
                          <span className="text-[9px] font-medium leading-none tracking-wide">{t("settings.logo.none")}</span>
                        </div>
                      )}
                    </div>

                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-neutral-800">{t("settings.logo.title")}</p>
                      <p className="text-xs text-neutral-600">{t("settings.logo.description")}</p>
                    </div>

                    <div className="flex items-center gap-2">
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/png,image/jpeg,image/svg+xml"
                        className="hidden"
                        onChange={(event) => {
                          const file = event.target.files?.[0] ?? null;
                          if (file && file.size > 500_000) {
                            setLogoNotice(t("settings.logo.error_too_large"));
                            event.target.value = "";
                            return;
                          }
                          setLogoFile(file);
                          setLogoNotice(null);
                          if (!file) {
                            return;
                          }
                          const reader = new FileReader();
                          reader.onload = () => setLogoPreviewUrl(typeof reader.result === "string" ? reader.result : null);
                          reader.onerror = () => setLogoNotice(t("settings.logo.error_read"));
                          reader.readAsDataURL(file);
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
                        {logoFile ? t("settings.logo.replace") : t("settings.logo.upload")}
                      </Button>
                      {logoFile ? (
                        <Button
                          type="button"
                          variant="ghost"
                          onClick={() => {
                            setLogoFile(null);
                            setLogoPreviewUrl(null);
                            if (fileInputRef.current) {
                              fileInputRef.current.value = "";
                            }
                          }}
                        >
                          <Trash2 className="h-4 w-4" />
                          {t("common.remove")}
                        </Button>
                      ) : null}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  <FormField id="service_name" label={t("settings.business.service_name")} required>
                    <Input
                      id="service_name"
                      className="h-[36px]"
                      value={form.service_name}
                      onChange={(event) => setForm((prev) => ({ ...prev, service_name: event.target.value }))}
                    />
                  </FormField>
                  <FormField id="phone" label={t("common.phone")} required hint={t("settings.business.phone_hint")}>
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
                    <h3 className="text-sm font-semibold text-neutral-900">{t("settings.region.title")}</h3>
                    <p className="mt-1 text-xs text-neutral-600">{t("settings.region.description")}</p>
                  </div>

                  <FormField
                    id="address"
                    label={t("settings.address.label")}
                    hint={t("settings.address.hint")}
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
                          <span className="text-neutral-500">{t("settings.timezone.label")}:</span>
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
                          {timezoneManualOverride ? <Badge tone="neutral">{t("settings.timezone.manual")}</Badge> : null}
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
                              {t("settings.timezone.use_auto")}
                            </Button>
                          ) : null}
                        </div>
                        <p className="mt-1 text-xs text-neutral-600">
                          {timezoneManualOverride ? t("settings.timezone.manual_enabled") : timezoneHelperText}
                        </p>

                        {timezonePickerOpen ? (
                          <div className="absolute left-0 top-[calc(100%+8px)] z-30 w-full rounded-md border border-neutral-200 bg-neutral-0 p-2 shadow-md">
                            <Combobox
                              id="timezone-manual-override"
                              name="timezone-manual-override"
                              value={timezoneDraft}
                              onChange={setTimezoneDraft}
                              options={mergedTimezoneOptions}
                              placeholder={t("settings.timezone.select")}
                              searchPlaceholder={t("settings.timezone.search")}
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
                                {t("common.cancel")}
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
                                {t("settings.timezone.apply")}
                              </Button>
                            </div>
                          </div>
                        ) : null}
                      </div>
                    </div>
                  </FormField>

                  <FormField id="currency" label={t("settings.currency.label")} required hint={t("settings.currency.hint")}>
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
                            {t("settings.currency.suggested")}: {currencySuggestion}
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
                              {t("settings.currency.apply_suggestion")}
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
                  <h2 className="text-[16px] font-semibold text-neutral-900">{t("settings.preferences.title")}</h2>
                  <p className="mt-1 text-sm text-neutral-600">{t("settings.preferences.description")}</p>
                </div>

                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  <div className="space-y-1.5">
                    <p className="text-xs font-semibold uppercase tracking-wide text-neutral-600">{t("settings.preferences.language")}</p>
                    <div className="grid grid-cols-2 gap-1 rounded-md border border-neutral-200 bg-neutral-50 p-1">
                      <button
                        type="button"
                        className={`h-8 rounded-md px-2 text-xs font-medium transition-colors ${
                          locale === "ru" ? "bg-neutral-0 text-neutral-900 shadow-sm" : "text-neutral-600 hover:bg-neutral-100"
                        }`}
                        onClick={() => setLocale("ru")}
                      >
                        {t("locale.russian")}
                      </button>
                      <button
                        type="button"
                        className={`h-8 rounded-md px-2 text-xs font-medium transition-colors ${
                          locale === "en" ? "bg-neutral-0 text-neutral-900 shadow-sm" : "text-neutral-600 hover:bg-neutral-100"
                        }`}
                        onClick={() => setLocale("en")}
                      >
                        {t("locale.english")}
                      </button>
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <p className="text-xs font-semibold uppercase tracking-wide text-neutral-600">{t("settings.preferences.theme")}</p>
                    <div className="grid grid-cols-2 gap-1 rounded-md border border-neutral-200 bg-neutral-50 p-1">
                      <button
                        type="button"
                        className={`inline-flex h-8 items-center justify-center gap-1 rounded-md px-2 text-xs font-medium transition-colors ${
                          theme === "light" ? "bg-neutral-0 text-neutral-900 shadow-sm" : "text-neutral-600 hover:bg-neutral-100"
                        }`}
                        onClick={() => setTheme("light")}
                      >
                        <Sun className="h-3.5 w-3.5" />
                        {t("shell.theme.light")}
                      </button>
                      <button
                        type="button"
                        className={`inline-flex h-8 items-center justify-center gap-1 rounded-md px-2 text-xs font-medium transition-colors ${
                          theme === "dark" ? "bg-neutral-0 text-neutral-900 shadow-sm" : "text-neutral-600 hover:bg-neutral-100"
                        }`}
                        onClick={() => setTheme("dark")}
                      >
                        <Moon className="h-3.5 w-3.5" />
                        {t("shell.theme.dark")}
                      </button>
                    </div>
                  </div>
                </div>
              </section>

              <section className="space-y-3 rounded-md border border-neutral-200 p-4">
                <div>
                  <h2 className="text-[16px] font-semibold text-neutral-900">{t("settings.notes.title")}</h2>
                  <p className="mt-1 text-sm text-neutral-600">{t("settings.notes.description")}</p>
                </div>
                <FormField id="working_hours_note" label={t("settings.notes.field_label")}>
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

            <div className="sticky bottom-0 border-t border-neutral-200 bg-neutral-50 px-4 py-3 pb-[max(12px,env(safe-area-inset-bottom))]">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs text-neutral-600">{t("settings.footer.note")}</p>
                <Button type="submit" variant="primary" loading={updateMutation.isPending}>
                  {t("settings.save")}
                </Button>
              </div>
            </div>
          </form>
        ) : null}
      </StateBoundary>
    </PageLayout>
  );
}
