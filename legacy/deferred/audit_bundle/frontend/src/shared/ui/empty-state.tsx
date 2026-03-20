import { Card } from "@/design-system/primitives/card";

type EmptyStateProps = {
  title: string;
  description?: string;
  action?: React.ReactNode;
};

export function EmptyState({ title, description, action }: EmptyStateProps): JSX.Element {
  return (
    <Card className="p-4 text-center">
      <h3 className="text-lg font-semibold text-neutral-900">{title}</h3>
      {description ? <p className="mt-1 text-sm text-neutral-600">{description}</p> : null}
      {action ? <div className="mt-3 flex justify-center">{action}</div> : null}
    </Card>
  );
}
