"use client";

import { useMemo } from "react";

import { Select } from "@/design-system/primitives";
import { useSwitchWorkspaceMutation, useWorkspaceQuery } from "@/features/workspace/hooks";
import { useWorkspaceStore } from "@/features/workspace/model/workspace-store";

type WorkspaceSwitcherProps = {
  compact?: boolean;
  hideError?: boolean;
};

export function WorkspaceSwitcher({ compact = false, hideError = false }: WorkspaceSwitcherProps): JSX.Element {
  const workspaceQuery = useWorkspaceQuery();
  const switchWorkspaceMutation = useSwitchWorkspaceMutation();
  const activeWorkspaceId = useWorkspaceStore((state) => state.activeWorkspaceId);

  const options = useMemo(() => workspaceQuery.data?.workspaces ?? [], [workspaceQuery.data?.workspaces]);

  const selectedWorkspaceId = activeWorkspaceId ?? workspaceQuery.data?.activeWorkspaceId ?? "";

  const onChangeWorkspace = async (workspaceId: string): Promise<void> => {
    if (!workspaceId || workspaceId === selectedWorkspaceId) {
      return;
    }

    await switchWorkspaceMutation.mutateAsync({ workspaceId });
  };

  return (
    <div className={compact ? "w-[172px]" : "min-w-[180px] max-w-[240px]"}>
      <label className="sr-only" htmlFor="workspace-switcher">
        Active workspace
      </label>
      <Select
        id="workspace-switcher"
        variant={compact ? "subtle" : "default"}
        className={
          compact
            ? "h-[32px] border-transparent bg-neutral-100 px-[10px] hover:border-neutral-300 hover:bg-neutral-0 focus-visible:ring-1 focus-visible:ring-neutral-300"
            : undefined
        }
        value={selectedWorkspaceId}
        title="Switch workspace"
        onChange={(event) => {
          void onChangeWorkspace(event.target.value);
        }}
        disabled={workspaceQuery.isPending || switchWorkspaceMutation.isPending || options.length === 0}
      >
        {options.length === 0 ? <option value="">Workspace loading</option> : null}
        {options.map((workspace) => (
          <option key={workspace.id} value={workspace.id} disabled={!workspace.isActive}>
            {workspace.name}
          </option>
        ))}
      </Select>
      {!hideError && switchWorkspaceMutation.error ? (
        <p className="mt-1 text-xs text-error">{switchWorkspaceMutation.error.message}</p>
      ) : null}
    </div>
  );
}
