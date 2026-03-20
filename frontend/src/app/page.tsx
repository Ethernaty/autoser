import { redirect } from "next/navigation";

import { ROUTES } from "@/core/config/routes";

export default function RootPage(): null {
  redirect(ROUTES.app);
}
