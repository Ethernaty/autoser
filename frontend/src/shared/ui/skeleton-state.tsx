import { Card } from "@/design-system/primitives/card";

export function SkeletonState({ variant = "section" }: { variant?: "page" | "section" | "table" }): JSX.Element {
  if (variant === "table") {
    return (
      <Card className="space-y-2 p-3">
        <div className="h-3 w-48 animate-pulse rounded bg-neutral-200" />
        {Array.from({ length: 8 }).map((_, index) => (
          <div key={index} className="h-4 w-full animate-pulse rounded bg-neutral-100" />
        ))}
      </Card>
    );
  }

  if (variant === "page") {
    return (
      <div className="mx-auto w-full max-w-content space-y-3 p-3 md:p-4">
        <div className="h-6 w-64 animate-pulse rounded bg-neutral-200" />
        <Card className="space-y-2 p-3">
          {Array.from({ length: 5 }).map((_, index) => (
            <div key={index} className="h-4 w-full animate-pulse rounded bg-neutral-100" />
          ))}
        </Card>
      </div>
    );
  }

  return (
    <Card className="space-y-2 p-3">
      {Array.from({ length: 3 }).map((_, index) => (
        <div key={index} className="h-4 w-full animate-pulse rounded bg-neutral-100" />
      ))}
    </Card>
  );
}
