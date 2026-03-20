import { ClientDetailScreen } from "@/features/workspace/ui";

export default function ClientDetailPage({
  params
}: {
  params: { clientId: string };
}): JSX.Element {
  return <ClientDetailScreen clientId={params.clientId} />;
}
