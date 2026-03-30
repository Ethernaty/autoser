"use client";

import { LogOut } from "lucide-react";

import { Button } from "@/design-system/primitives/button";
import { useLogoutMutation } from "@/features/auth/hooks/use-logout-mutation";
import { useI18n } from "@/shared/i18n";

export function LogoutAction(): JSX.Element {
  const logoutMutation = useLogoutMutation();
  const { t } = useI18n();

  return (
    <Button
      variant="secondary"
      size="sm"
      onClick={() => logoutMutation.mutate()}
      loading={logoutMutation.isPending}
      title={t("shell.logout")}
      aria-label={t("shell.logout")}
    >
      <LogOut className="h-2.5 w-2.5" />
      <span className="hidden md:inline">{t("shell.logout")}</span>
    </Button>
  );
}
