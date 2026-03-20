"use client";

import { LogOut } from "lucide-react";

import { Button } from "@/design-system/primitives/button";
import { useLogoutMutation } from "@/features/auth/hooks/use-logout-mutation";

export function LogoutAction(): JSX.Element {
  const logoutMutation = useLogoutMutation();

  return (
    <Button
      variant="secondary"
      size="sm"
      onClick={() => logoutMutation.mutate()}
      loading={logoutMutation.isPending}
      title="Logout"
      aria-label="Logout"
    >
      <LogOut className="h-2.5 w-2.5" />
      <span className="hidden md:inline">Logout</span>
    </Button>
  );
}
