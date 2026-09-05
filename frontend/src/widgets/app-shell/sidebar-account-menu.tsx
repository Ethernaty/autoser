"use client";

import Link from "next/link";
import type { Route } from "next";
import { ChevronDown, LogOut, Moon, Settings, Sun, User } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { ROUTES } from "@/core/config/routes";
import { cn } from "@/core/lib/utils";
import { Button } from "@/design-system/primitives";
import { useLogoutMutation } from "@/features/auth/hooks/use-logout-mutation";
import { useI18n } from "@/shared/i18n";
import { useTheme } from "@/shared/theme/theme-provider";

type SidebarAccountMenuProps = {
  collapsed: boolean;
  workspaceSlug: string;
  roleLabel: string;
  userEmail: string;
  userInitials: string;
};

export function SidebarAccountMenu({
  collapsed,
  workspaceSlug,
  roleLabel,
  userEmail,
  userInitials
}: SidebarAccountMenuProps): JSX.Element {
  const { locale, setLocale, t } = useI18n();
  const { theme, setTheme } = useTheme();
  const logoutMutation = useLogoutMutation();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const roleText = useMemo(() => {
    if (roleLabel === "owner") return t("roles.owner");
    if (roleLabel === "admin") return t("roles.admin");
    if (roleLabel === "manager") return t("roles.manager");
    if (roleLabel === "employee") return t("roles.employee");
    return roleLabel;
  }, [roleLabel, t]);

  useEffect(() => {
    const onPointerDown = (event: MouseEvent): void => {
      if (!rootRef.current) return;
      if (!rootRef.current.contains(event.target as Node)) setOpen(false);
    };
    const onEscape = (event: KeyboardEvent): void => {
      if (event.key === "Escape") setOpen(false);
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
          "w-full rounded-xl border border-white/20 bg-white/12 text-white/90 transition-colors hover:border-white/30 hover:bg-white/16",
          collapsed ? "flex h-10 items-center justify-center" : "flex items-center gap-2.5 px-3 py-2"
        )}
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-haspopup="menu"
      >
        <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-white/30 bg-white/20 text-xs font-semibold text-white">
          {userInitials}
        </span>

        {!collapsed ? (
          <>
            <div className="min-w-0 text-left">
              <p className="truncate text-xs font-semibold">{workspaceSlug}</p>
              <p className="truncate text-[11px] text-white/70">{roleText}</p>
            </div>
            <ChevronDown className={cn("ml-auto h-4 w-4 shrink-0 text-white/80 transition-transform", open && "rotate-180")} />
          </>
        ) : null}
      </button>

      {open ? (
        <div
          className={cn(
            "absolute z-[120] w-[min(88vw,280px)] rounded-xl border border-neutral-200 bg-neutral-0 p-2 shadow-md",
            collapsed ? "bottom-0 left-[calc(100%+8px)]" : "bottom-[calc(100%+8px)] left-0"
          )}
          role="menu"
        >
          <div className="rounded-lg border border-neutral-200 bg-neutral-50 px-2 py-2">
            <p className="truncate text-xs font-semibold text-neutral-800">{userEmail}</p>
            <p className="mt-1 text-xs text-neutral-600">
              {t("shell.role")}: {roleText}
            </p>
          </div>

          <div className="mt-1 rounded-lg border border-neutral-200 px-2 py-1.5">
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

          <div className="mt-1 rounded-lg border border-neutral-200 px-2 py-1.5">
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
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="flex h-8 w-full items-center justify-start gap-2 rounded-md px-2 text-error hover:bg-error/10"
              onClick={() => {
                logoutMutation.mutate();
                setOpen(false);
              }}
              disabled={logoutMutation.isPending}
            >
              <LogOut className="h-4 w-4" />
              {logoutMutation.isPending ? t("shell.logging_out") : t("shell.logout")}
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

