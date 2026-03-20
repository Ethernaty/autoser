import { VehicleDetailScreen } from "@/features/workspace/ui";

export default function VehicleDetailPage({
  params
}: {
  params: { vehicleId: string };
}): JSX.Element {
  return <VehicleDetailScreen vehicleId={params.vehicleId} />;
}
