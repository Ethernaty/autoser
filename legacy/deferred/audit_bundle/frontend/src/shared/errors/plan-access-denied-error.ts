export class PlanAccessDeniedError extends Error {
  readonly code = "plan_access_denied" as const;
  readonly status: number;

  constructor(message: string, status = 403) {
    super(message);
    this.name = "PlanAccessDeniedError";
    this.status = status;
  }
}
