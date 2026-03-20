import { AlertTriangle } from "lucide-react";

import { Button } from "@/design-system/primitives/button";
import { Card } from "@/design-system/primitives/card";

type ErrorStateProps = {
  title: string;
  description?: string;
  onRetry?: () => void;
};

export function ErrorState({ title, description, onRetry }: ErrorStateProps): JSX.Element {
  return (
    <Card className="border-danger/30 p-4">
      <div className="flex items-start gap-2">
        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 text-danger" />
        <div className="min-w-0 flex-1">
          <h3 className="text-lg font-semibold text-neutral-900">{title}</h3>
          {description ? <p className="mt-1 text-sm text-neutral-700">{description}</p> : null}
          {onRetry ? (
            <div className="mt-3">
              <Button variant="secondary" onClick={onRetry}>
                Retry
              </Button>
            </div>
          ) : null}
        </div>
      </div>
    </Card>
  );
}
