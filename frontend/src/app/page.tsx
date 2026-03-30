import type { Metadata } from "next";

import { LandingPage } from "@/features/landing/ui";

export const metadata: Metadata = {
  title: "AutoService CRM — CRM для автосервиса в браузере",
  description:
    "AutoService CRM помогает автосервисам и СТО держать в порядке клиентов, автомобили, заказ-наряды, сотрудников и расчёт выплат в одной браузерной системе.",
  openGraph: {
    title: "AutoService CRM — CRM для автосервиса в браузере",
    description:
      "Практичная CRM для СТО: приёмка, заказ-наряды, история по клиентам и автомобилям, контроль сотрудников и прозрачная операционка.",
    type: "website",
    locale: "ru_RU",
    siteName: "AutoService CRM"
  }
};

export default function RootPage(): JSX.Element {
  return <LandingPage />;
}

