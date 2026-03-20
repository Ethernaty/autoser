import { redirect } from "next/navigation";

import { ROUTES } from "@/core/config/routes";

export default function LegacyNewOrderPage(): null {
  redirect(ROUTES.workOrders);
}
