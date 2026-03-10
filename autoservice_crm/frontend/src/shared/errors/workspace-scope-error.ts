export class WorkspaceScopeError extends Error {
  readonly expectedWorkspaceId: string;
  readonly actualWorkspaceId: string | null;

  constructor({ expectedWorkspaceId, actualWorkspaceId, entity }: { expectedWorkspaceId: string; actualWorkspaceId: string | null; entity: string }) {
    super(`Workspace mismatch for ${entity}`);
    this.name = "WorkspaceScopeError";
    this.expectedWorkspaceId = expectedWorkspaceId;
    this.actualWorkspaceId = actualWorkspaceId;
  }
}

