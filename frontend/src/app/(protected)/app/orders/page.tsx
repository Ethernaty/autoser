import { redirect } from "next/navigation";

import { ROUTES } from "@/core/config/routes";

export default function LegacyOrdersPage(): null {
  redirect(ROUTES.workOrders);
}
