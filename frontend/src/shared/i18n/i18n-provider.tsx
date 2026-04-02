"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type PropsWithChildren } from "react";

import { APP_MESSAGES, DEFAULT_LOCALE, type AppLocale } from "@/shared/i18n/messages";

type I18nContextValue = {
  locale: AppLocale;
  setLocale: (locale: AppLocale) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
};

const STORAGE_KEY = "autoservice.crm.locale";
let hasWarnedMissingProvider = false;

const I18nContext = createContext<I18nContextValue | null>(null);

function formatMessage(locale: AppLocale, key: string, params?: Record<string, string | number>): string {
  const template = APP_MESSAGES[locale][key] ?? APP_MESSAGES[DEFAULT_LOCALE][key] ?? key;
  if (!params) {
    return template;
  }
  return Object.entries(params).reduce((value, [paramKey, paramValue]) => {
    return value.replace(new RegExp(`\\{${paramKey}\\}`, "g"), String(paramValue));
  }, template);
}

export function I18nProvider({ children }: PropsWithChildren): JSX.Element {
  const [locale, setLocaleState] = useState<AppLocale>(DEFAULT_LOCALE);

  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved === "ru" || saved === "en") {
      setLocaleState(saved);
    }
  }, []);

  const setLocale = useCallback((nextLocale: AppLocale) => {
    setLocaleState(nextLocale);
    window.localStorage.setItem(STORAGE_KEY, nextLocale);
  }, []);

  const t = useCallback(
    (key: string, params?: Record<string, string | number>) => {
      return formatMessage(locale, key, params);
    },
    [locale]
  );

  const value = useMemo<I18nContextValue>(
    () => ({
      locale,
      setLocale,
      t
    }),
    [locale, setLocale, t]
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const value = useContext(I18nContext);
  if (!value) {
    if (process.env.NODE_ENV !== "production" && !hasWarnedMissingProvider) {
      hasWarnedMissingProvider = true;
      console.warn("useI18n called outside I18nProvider. Falling back to DEFAULT_LOCALE messages.");
    }

    return {
      locale: DEFAULT_LOCALE,
      setLocale: () => {
        // Fallback mode outside provider: locale changes are intentionally no-op.
      },
      t: (key, params) => formatMessage(DEFAULT_LOCALE, key, params)
    };
  }
  return value;
}
