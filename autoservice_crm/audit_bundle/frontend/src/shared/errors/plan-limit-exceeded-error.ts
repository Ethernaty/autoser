export class PlanLimitExceededError extends Error {
  readonly code = "plan_limit_exceeded" as const;
  readonly limitType: string;
  readonly status: number;

  constructor({ limitType, message, status = 402 }: { limitType: string; message: string; status?: number }) {
    super(message);
    this.name = "PlanLimitExceededError";
    this.limitType = limitType;
    this.status = status;
  }
}
