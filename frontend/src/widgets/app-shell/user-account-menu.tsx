"use client";

import Link from "next/link";
import type { Route } from "next";
import { ChevronDown, LogOut, Moon, Settings, Sun, User } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { ROUTES } from "@/core/config/routes";
import { cn } from "@/core/lib/utils";
import { useLogoutMutation } from "@/features/auth/hooks/use-logout-mutation";
import { useAuthStore } from "@/features/auth/model/auth-store";
import { useI18n } from "@/shared/i18n";
import { useTheme } from "@/shared/theme/theme-provider";

export function UserAccountMenu(): JSX.Element {
  const session = useAuthStore((state) => state.session);
  const logoutMutation = useLogoutMutation();
  const { locale, setLocale, t } = useI18n();
  const { theme, setTheme } = useTheme();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const initials = useMemo(() => {
    const email = session?.user.email?.trim();
    if (!email) {
      return "U";
    }
    return email.slice(0, 2).toUpperCase();
  }, [session?.user.email]);

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

  return (
    <div className="relative" ref={rootRef}>
      <button
        type="button"
        className={cn(
          "flex h-[32px] items-center gap-1.5 rounded-md border border-transparent bg-neutral-100 px-[10px] text-left text-neutral-700 transition-colors",
          "hover:border-neutral-300 hover:bg-neutral-0 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-neutral-300"
        )}
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-haspopup="menu"
      >
        <span className="inline-flex h-[24px] w-[24px] items-center justify-center rounded-full bg-neutral-300 text-[11px] font-semibold text-neutral-700">
          {initials}
        </span>
        <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-180")} />
      </button>

      {open ? (
        <div
          className="absolute right-0 top-[calc(100%+8px)] z-[120] w-[280px] rounded-md border border-neutral-200 bg-neutral-0 p-2 shadow-md"
          role="menu"
        >
          <div className="rounded-md border border-neutral-200 bg-neutral-50 px-2 py-2">
            <p className="truncate text-xs font-semibold text-neutral-800">{session?.user.email ?? t("shell.unknown_user")}</p>
            <p className="mt-1 text-xs text-neutral-600">
              {t("shell.role")}: {session?.role ?? t("common.unknown")}
            </p>
          </div>

          <div className="mt-1 rounded-md border border-neutral-200 px-2 py-1.5">
            <label htmlFor="locale-select" className="text-[11px] font-semibold uppercase tracking-wide text-neutral-500">
              {t("shell.language")}
            </label>
            <div id="locale-select" className="mt-1 grid grid-cols-2 gap-1 rounded-md border border-neutral-200 bg-neutral-50 p-1">
              <button
                type="button"
                className={cn(
                  "h-7 rounded-md px-2 text-xs font-medium transition-colors",
                  locale === "ru" ? "bg-neutral-0 text-neutral-900 shadow-sm" : "text-neutral-600 hover:bg-neutral-100"
                )}
                onClick={() => setLocale("ru")}
              >
                {t("locale.russian")}
              </button>
              <button
                type="button"
                className={cn(
                  "h-7 rounded-md px-2 text-xs font-medium transition-colors",
                  locale === "en" ? "bg-neutral-0 text-neutral-900 shadow-sm" : "text-neutral-600 hover:bg-neutral-100"
                )}
                onClick={() => setLocale("en")}
              >
                {t("locale.english")}
              </button>
            </div>
          </div>

          <div className="mt-1 rounded-md border border-neutral-200 px-2 py-1.5">
            <label htmlFor="theme-select" className="text-[11px] font-semibold uppercase tracking-wide text-neutral-500">
              {t("shell.theme")}
            </label>
            <div id="theme-select" className="mt-1 grid grid-cols-2 gap-1 rounded-md border border-neutral-200 bg-neutral-50 p-1">
              <button
                type="button"
                className={cn(
                  "inline-flex h-7 items-center justify-center gap-1 rounded-md px-2 text-xs font-medium transition-colors",
                  theme === "light" ? "bg-neutral-0 text-neutral-900 shadow-sm" : "text-neutral-600 hover:bg-neutral-100"
                )}
                onClick={() => setTheme("light")}
              >
                <Sun className="h-3.5 w-3.5" />
                {t("shell.theme.light")}
              </button>
              <button
                type="button"
                className={cn(
                  "inline-flex h-7 items-center justify-center gap-1 rounded-md px-2 text-xs font-medium transition-colors",
                  theme === "dark" ? "bg-neutral-0 text-neutral-900 shadow-sm" : "text-neutral-600 hover:bg-neutral-100"
                )}
                onClick={() => setTheme("dark")}
              >
                <Moon className="h-3.5 w-3.5" />
                {t("shell.theme.dark")}
              </button>
            </div>
          </div>

          <div className="mt-1 space-y-1">
            <Link
              href={ROUTES.profile as Route}
              className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm text-neutral-800 hover:bg-neutral-100"
              onClick={() => setOpen(false)}
            >
              <User className="h-4 w-4" />
              {t("shell.profile")}
            </Link>
            <Link
              href={ROUTES.settings as Route}
              className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm text-neutral-800 hover:bg-neutral-100"
              onClick={() => setOpen(false)}
            >
              <Settings className="h-4 w-4" />
              {t("shell.settings")}
            </Link>
          </div>

          <div className="mt-1 border-t border-neutral-100 pt-1">
            <button
              type="button"
              className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm text-error hover:bg-error/10"
              onClick={() => {
                logoutMutation.mutate();
                setOpen(false);
              }}
              disabled={logoutMutation.isPending}
            >
              <LogOut className="h-4 w-4" />
              {logoutMutation.isPending ? t("shell.logging_out") : t("shell.logout")}
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
