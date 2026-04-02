"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePathname } from "next/navigation";
import { Car, ClipboardList, LayoutDashboard, Menu, UsersRound } from "lucide-react";

import { ROUTES } from "@/core/config/routes";
import { cn } from "@/core/lib/utils";
import { useI18n } from "@/shared/i18n";
import { useUiStore } from "@/shared/ui/ui-store";

const primaryMobileItems = [
  { href: ROUTES.dashboard, labelKey: "shell.nav.dashboard", icon: LayoutDashboard },
  { href: ROUTES.workOrders, labelKey: "shell.nav.work_orders", icon: ClipboardList },
  { href: ROUTES.clients, labelKey: "shell.nav.clients", icon: UsersRound },
  { href: ROUTES.vehicles, labelKey: "shell.nav.vehicles", icon: Car }
] as const;

export function MobileBottomNav(): JSX.Element {
  const pathname = usePathname();
  const setMobileSidebarOpen = useUiStore((state) => state.setMobileSidebarOpen);
  const { locale, t } = useI18n();

  const moreLabel = locale === "ru" ? "Ещё" : "More";

  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-neutral-200 bg-neutral-0/95 backdrop-blur md:hidden" aria-label={t("shell.nav.primary")}>
      <div className="mx-auto w-full max-w-content px-2 pb-[max(8px,env(safe-area-inset-bottom))] pt-1.5">
        <ul className="grid grid-cols-5 gap-1">
          {primaryMobileItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
            const Icon = item.icon;

            return (
              <li key={item.href}>
                <Link
                  href={item.href as Route}
                  className={cn(
                    "flex min-h-[52px] flex-col items-center justify-center gap-0.5 rounded-md px-1 py-1 text-[10px] font-semibold",
                    isActive ? "bg-primary/10 text-primary" : "text-neutral-600"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  <span className="truncate">{t(item.labelKey)}</span>
                </Link>
              </li>
            );
          })}

          <li>
            <button
              type="button"
              className="flex min-h-[52px] w-full flex-col items-center justify-center gap-0.5 rounded-md px-1 py-1 text-[10px] font-semibold text-neutral-600"
              onClick={() => setMobileSidebarOpen(true)}
              aria-label={moreLabel}
            >
              <Menu className="h-4 w-4" />
              <span className="truncate">{moreLabel}</span>
            </button>
          </li>
        </ul>
      </div>
    </nav>
  );
}
