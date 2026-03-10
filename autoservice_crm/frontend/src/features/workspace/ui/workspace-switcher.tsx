"use client";

import { useMemo } from "react";

import { useSwitchWorkspaceMutation, useWorkspaceQuery } from "@/features/workspace/hooks";
import { useWorkspaceStore } from "@/features/workspace/model/workspace-store";

export function WorkspaceSwitcher(): JSX.Element {
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
    <div className="min-w-[160px] max-w-[220px]">
      <label className="sr-only" htmlFor="workspace-switcher">
        Active workspace
      </label>
      <select
        id="workspace-switcher"
        className="h-4 w-full rounded-sm border border-neutral-300 bg-neutral-0 px-1.5 text-sm text-neutral-900 outline-none transition focus:border-neutral-500 disabled:cursor-not-allowed disabled:opacity-60"
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
      </select>
      {switchWorkspaceMutation.error ? (
        <p className="mt-1 text-xs text-error">{switchWorkspaceMutation.error.message}</p>
      ) : null}
    </div>
  );
}
