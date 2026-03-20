import { redirect } from "next/navigation";

import { ROUTES } from "@/core/config/routes";

export default function LegacyCashDeskPage(): null {
  redirect(ROUTES.dashboard);
}
