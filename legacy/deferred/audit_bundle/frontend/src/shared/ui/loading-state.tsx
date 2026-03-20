import { Card } from "@/design-system/primitives/card";

export function LoadingState({ label = "Loading" }: { label?: string }): JSX.Element {
  return (
    <Card className="flex items-center gap-2 p-3">
      <span className="h-2 w-2 animate-spin rounded-full border-2 border-neutral-700 border-r-transparent" />
      <span className="text-sm text-neutral-700">{label}</span>
    </Card>
  );
}
