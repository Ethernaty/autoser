import { AppLayout } from "@/widgets/app-shell/app-layout";

export default function InternalAppLayout({
  children,
  modal
}: {
  children: React.ReactNode;
  modal: React.ReactNode;
}): JSX.Element {
  return <AppLayout modal={modal}>{children}</AppLayout>;
}
