"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";
import {
  LayoutDashboard,
  PanelLeftClose,
  Settings,
  UserCog,
  UsersRound,
  Car,
  ClipboardList,
  LifeBuoy
} from "lucide-react";

import { ROUTES } from "@/core/config/routes";
import { Button } from "@/design-system/primitives/button";
import { cn } from "@/core/lib/utils";
import { useAuthStore } from "@/features/auth/model/auth-store";
import { useI18n } from "@/shared/i18n";
import { useUiStore } from "@/shared/ui/ui-store";

const navGroups = [
  {
    labelKey: "shell.nav.operations",
    items: [
      { labelKey: "shell.nav.dashboard", href: ROUTES.dashboard, icon: LayoutDashboard },
      { labelKey: "shell.nav.work_orders", href: ROUTES.workOrders, icon: ClipboardList },
      { labelKey: "shell.nav.clients", href: ROUTES.clients, icon: UsersRound },
      { labelKey: "shell.nav.vehicles", href: ROUTES.vehicles, icon: Car }
    ]
  },
  {
    labelKey: "shell.nav.team",
    items: [{ labelKey: "shell.nav.employees", href: ROUTES.employees, icon: UserCog }]
  },
  {
    labelKey: "shell.nav.system",
    items: [
      { labelKey: "shell.nav.support", href: ROUTES.support, icon: LifeBuoy },
      { labelKey: "shell.nav.settings", href: ROUTES.settings, icon: Settings }
    ]
  }
] as const;

export function Sidebar({ collapsed }: { collapsed: boolean }): JSX.Element {
  const pathname = usePathname();
  const setCollapsed = useUiStore((state) => state.setSidebarCollapsed);
  const mobileSidebarOpen = useUiStore((state) => state.mobileSidebarOpen);
  const setMobileSidebarOpen = useUiStore((state) => state.setMobileSidebarOpen);
  const session = useAuthStore((state) => state.session);
  const { t } = useI18n();

  useEffect(() => {
    setMobileSidebarOpen(false);
  }, [pathname, setMobileSidebarOpen]);

  useEffect(() => {
    if (!mobileSidebarOpen) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [mobileSidebarOpen]);

  const renderNavigation = (isCollapsed: boolean, onItemNavigate?: () => void): JSX.Element => (
    <nav className={cn("space-y-4 p-2", isCollapsed ? "px-1.5" : "px-2")} aria-label={t("shell.nav.primary")}>
      {navGroups.map((group) => (
        <div key={group.labelKey} className="space-y-1">
          {!isCollapsed ? (
            <p className="px-2 text-[11px] font-semibold uppercase tracking-wide text-neutral-500">{t(group.labelKey)}</p>
          ) : null}
          {group.items.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onItemNavigate}
                className={cn(
                  "relative flex h-9 w-full items-center rounded-md border text-sm transition-colors",
                  isCollapsed ? "justify-center px-0" : "gap-2 px-2.5",
                  isActive
                    ? "border-primary/25 bg-primary/10 text-primary"
                    : "border-transparent text-neutral-700 hover:border-neutral-200 hover:bg-neutral-50 hover:text-neutral-900"
                )}
                data-ui="interactive"
              >
                <span
                  aria-hidden
                  className={cn(
                    "absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r-full transition-colors",
                    isActive ? "bg-primary" : "bg-transparent"
                  )}
                />
                <item.icon className="h-4 w-4 shrink-0" />
                {!isCollapsed ? <span className="truncate font-medium">{t(item.labelKey)}</span> : null}
              </Link>
            );
          })}
        </div>
      ))}
    </nav>
  );

  return (
    <>
      <aside
        className={cn(
          "fixed left-0 top-0 z-20 hidden h-screen border-r border-neutral-200 bg-neutral-0 shadow-sm transition-all duration-150 ease-standard md:block",
          collapsed ? "w-sidebar-collapsed" : "w-sidebar"
        )}
      >
        <div className={cn("flex h-header items-center border-b border-neutral-200 px-3", collapsed ? "justify-center" : "justify-between")}>
          {!collapsed ? (
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-neutral-900">{t("shell.brand")}</p>
              <p className="truncate text-xs text-neutral-500">{session?.tenant.slug ?? t("shell.workspace_fallback")}</p>
            </div>
          ) : null}
          <Button variant="ghost" size="sm" onClick={() => setCollapsed(!collapsed)} aria-label={t("shell.toggle_sidebar")}>
            <PanelLeftClose className="h-4 w-4" />
          </Button>
        </div>
        {renderNavigation(collapsed)}
      </aside>

      <div className={cn("fixed inset-0 z-[60] md:hidden", mobileSidebarOpen ? "pointer-events-auto" : "pointer-events-none")}>
        <button
          type="button"
          className={cn("absolute inset-0 bg-neutral-950/35 transition-opacity", mobileSidebarOpen ? "opacity-100" : "opacity-0")}
          onClick={() => setMobileSidebarOpen(false)}
          aria-label={t("shell.toggle_sidebar")}
        />

        <aside
          className={cn(
            "absolute left-0 top-0 h-full w-[272px] border-r border-neutral-200 bg-neutral-0 shadow-lg transition-transform duration-200 ease-standard",
            mobileSidebarOpen ? "translate-x-0" : "-translate-x-full"
          )}
        >
          <div className="flex h-header items-center justify-between border-b border-neutral-200 px-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-neutral-900">{t("shell.brand")}</p>
              <p className="truncate text-xs text-neutral-500">{session?.tenant.slug ?? t("shell.workspace_fallback")}</p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setMobileSidebarOpen(false)} aria-label={t("shell.toggle_sidebar")}>
              <PanelLeftClose className="h-4 w-4" />
            </Button>
          </div>
          {renderNavigation(false, () => setMobileSidebarOpen(false))}
        </aside>
      </div>
    </>
  );
}
