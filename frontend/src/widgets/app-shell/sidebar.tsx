"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { Car, ClipboardList, LayoutDashboard, LifeBuoy, PanelLeftClose, Settings, UserCog, UsersRound, Wrench } from "lucide-react";

import { ROUTES } from "@/core/config/routes";
import { cn } from "@/core/lib/utils";
import { Button } from "@/design-system/primitives/button";
import { useAuthStore } from "@/features/auth/model/auth-store";
import { useI18n } from "@/shared/i18n";
import { useUiStore } from "@/shared/ui/ui-store";
import { SidebarAccountMenu } from "@/widgets/app-shell/sidebar-account-menu";

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
    if (!mobileSidebarOpen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [mobileSidebarOpen]);

  const userEmail = session?.user.email?.trim() || t("shell.unknown_user");
  const workspaceSlug = session?.tenant.slug || t("shell.workspace_fallback");
  const roleLabel = session?.role || "unknown";
  const userInitials = userEmail
    .split("@")[0]
    .split(/[\s._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("")
    .slice(0, 2) || "U";

  const renderNavigation = (isCollapsed: boolean, onItemNavigate?: () => void): JSX.Element => (
    <nav className={cn("space-y-5", isCollapsed ? "px-1.5" : "px-2.5")} aria-label={t("shell.nav.primary")}>
      {navGroups.map((group) => (
        <div key={group.labelKey} className="space-y-1.5">
          {!isCollapsed ? (
            <p className="px-2 text-[10px] font-semibold uppercase tracking-[0.08em] text-white/60">{t(group.labelKey)}</p>
          ) : null}
          <div className="space-y-1">
            {group.items.map((item) => {
              const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={onItemNavigate}
                  className={cn(
                    "relative flex w-full items-center rounded-xl border text-[13px] font-medium transition-colors",
                    isCollapsed ? "h-10 justify-center px-0" : "h-9 gap-2.5 px-3",
                    isActive
                      ? "border-white/25 bg-white/16 text-white shadow-[inset_0_0_0_1px_rgba(255,255,255,0.07)]"
                      : "border-transparent text-white/86 hover:border-white/15 hover:bg-white/10 hover:text-white"
                  )}
                >
                  <item.icon className="h-4 w-4 shrink-0" />
                  {!isCollapsed ? <span className="truncate">{t(item.labelKey)}</span> : null}
                  {isActive ? <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r-full bg-white" /> : null}
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </nav>
  );

  const renderBottomProfile = (isCollapsed: boolean): JSX.Element => (
    <div className={cn("border-t border-white/15 p-2.5", isCollapsed ? "px-1.5" : "px-2.5")}>
      <SidebarAccountMenu
        collapsed={isCollapsed}
        workspaceSlug={workspaceSlug}
        roleLabel={roleLabel}
        userEmail={userEmail}
        userInitials={userInitials}
      />
    </div>
  );

  return (
    <>
      <aside
        className={cn(
          "fixed left-0 top-0 z-30 hidden h-screen overflow-hidden transition-all duration-200 lg:block",
          collapsed ? "w-sidebar-collapsed" : "w-sidebar"
        )}
      >
        <div className="flex h-full flex-col border-r border-white/10 bg-[linear-gradient(180deg,#4D46CE_0%,#443DB7_45%,#37318F_100%)] text-white dark:bg-[linear-gradient(180deg,#2A296F_0%,#23225A_48%,#1C1C45_100%)]">
          <div className={cn("flex h-header items-center border-b border-white/15", collapsed ? "justify-center px-2" : "justify-between px-3")}>
            {!collapsed ? (
              <Link href={ROUTES.dashboard} className="min-w-0">
                <p className="truncate text-[15px] font-semibold text-white">{t("shell.brand")}</p>
                <p className="truncate text-[11px] text-white/75">{workspaceSlug}</p>
              </Link>
            ) : (
              <div className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-white/25 bg-white/12">
                <Wrench className="h-4 w-4" />
              </div>
            )}
            <Button
              variant="ghost"
              size="sm"
              className="h-8 min-w-8 border-none bg-transparent px-1.5 text-white/85 hover:bg-white/12 hover:text-white"
              onClick={() => setCollapsed(!collapsed)}
              aria-label={t("shell.toggle_sidebar")}
            >
              <PanelLeftClose className="h-4 w-4" />
            </Button>
          </div>

          <div className="flex-1 overflow-y-auto py-3">{renderNavigation(collapsed)}</div>
          {renderBottomProfile(collapsed)}
        </div>
      </aside>

      <div className={cn("fixed inset-0 z-[70] lg:hidden", mobileSidebarOpen ? "pointer-events-auto" : "pointer-events-none")}>
        <button
          type="button"
          className={cn("absolute inset-0 bg-neutral-950/40 transition-opacity", mobileSidebarOpen ? "opacity-100" : "opacity-0")}
          onClick={() => setMobileSidebarOpen(false)}
          aria-label={t("shell.toggle_sidebar")}
        />
        <aside
          className={cn(
            "absolute left-0 top-0 h-full w-[272px] overflow-hidden border-r border-white/10 bg-[linear-gradient(180deg,#4D46CE_0%,#443DB7_45%,#37318F_100%)] text-white shadow-2xl transition-transform duration-200 dark:bg-[linear-gradient(180deg,#2A296F_0%,#23225A_48%,#1C1C45_100%)]",
            mobileSidebarOpen ? "translate-x-0" : "-translate-x-full"
          )}
        >
          <div className="flex h-full flex-col">
            <div className="flex h-header items-center justify-between border-b border-white/15 px-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-white">{t("shell.brand")}</p>
                <p className="truncate text-xs text-white/75">{workspaceSlug}</p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 min-w-8 border-none bg-transparent px-1.5 text-white/85 hover:bg-white/12 hover:text-white"
                onClick={() => setMobileSidebarOpen(false)}
                aria-label={t("shell.toggle_sidebar")}
              >
                <PanelLeftClose className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex-1 overflow-y-auto py-3">{renderNavigation(false, () => setMobileSidebarOpen(false))}</div>
            {renderBottomProfile(false)}
          </div>
        </aside>
      </div>
    </>
  );
}
