export class RbacForbiddenError extends Error {
  readonly action: string;
  readonly role: string;

  constructor(action: string, role: string) {
    super(`Action ${action} is forbidden for role ${role}`);
    this.name = "RbacForbiddenError";
    this.action = action;
    this.role = role;
  }
}
