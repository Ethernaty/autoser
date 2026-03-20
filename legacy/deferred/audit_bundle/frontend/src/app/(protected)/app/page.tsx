import { redirect } from "next/navigation";

import { ROUTES } from "@/core/config/routes";

export default function ProtectedAppPage(): null {
  redirect(ROUTES.dashboard);
}
