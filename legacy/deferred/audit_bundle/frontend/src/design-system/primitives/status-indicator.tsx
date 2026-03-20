import { Badge } from "@/design-system/primitives/badge";

type Status = "online" | "degraded" | "offline" | "paused";
type Shape = "dot" | "pill";

const toneMap: Record<Status, "success" | "warning" | "error" | "neutral"> = {
  online: "success",
  degraded: "warning",
  offline: "error",
  paused: "neutral"
};

type StatusIndicatorProps = {
  status: Status;
  shape?: Shape;
  label?: string;
};

export function StatusIndicator({ status, shape = "pill", label }: StatusIndicatorProps): JSX.Element {
  if (shape === "dot") {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-neutral-700">
        <span
          className={
            "h-1.5 w-1.5 rounded-full " +
            (status === "online"
              ? "bg-success"
              : status === "degraded"
              ? "bg-warning"
              : status === "offline"
              ? "bg-error"
              : "bg-neutral-500")
          }
        />
        {label ?? status}
      </span>
    );
  }

  return <Badge tone={toneMap[status]}>{label ?? status}</Badge>;
}

