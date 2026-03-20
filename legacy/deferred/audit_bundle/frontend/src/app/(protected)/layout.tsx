import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ROUTES } from "@/core/config/routes";
import { ACCESS_COOKIE_NAME } from "@/features/auth/api/session-cookies";
import { ProtectedLayoutGuard } from "@/features/auth/ui/protected-layout-guard";
import { AppLayout } from "@/widgets/app-shell/app-layout";

export default function ProtectedLayout({
  children,
  modal
}: {
  children: React.ReactNode;
  modal: React.ReactNode;
}): JSX.Element {
  const accessToken = cookies().get(ACCESS_COOKIE_NAME)?.value;
  if (!accessToken) {
    redirect(ROUTES.login);
  }

  return (
    <ProtectedLayoutGuard>
      <AppLayout modal={modal}>{children}</AppLayout>
    </ProtectedLayoutGuard>
  );
}
