import { WorkOrderDetailScreen } from "@/features/workspace/ui";

export default function WorkOrderDetailPage({
  params
}: {
  params: { workOrderId: string };
}): JSX.Element {
  return <WorkOrderDetailScreen workOrderId={params.workOrderId} />;
}
