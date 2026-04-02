"use client";

import { useMemo } from "react";

import { Combobox } from "@/design-system/primitives";
import { useSwitchWorkspaceMutation, useWorkspaceQuery } from "@/features/workspace/hooks";
import { useWorkspaceStore } from "@/features/workspace/model/workspace-store";
import { useI18n } from "@/shared/i18n";

type WorkspaceSwitcherProps = {
  compact?: boolean;
  hideError?: boolean;
};

export function WorkspaceSwitcher({ compact = false, hideError = false }: WorkspaceSwitcherProps): JSX.Element {
  const { t } = useI18n();
  const workspaceQuery = useWorkspaceQuery();
  const switchWorkspaceMutation = useSwitchWorkspaceMutation();
  const activeWorkspaceId = useWorkspaceStore((state) => state.activeWorkspaceId);

  const options = useMemo(() => workspaceQuery.data?.workspaces ?? [], [workspaceQuery.data?.workspaces]);
  const comboboxOptions = useMemo(
    () =>
      options.map((workspace) => ({
        value: workspace.id,
        label: workspace.name,
        keywords: [workspace.slug]
      })),
    [options]
  );

  const selectedWorkspaceId = activeWorkspaceId ?? workspaceQuery.data?.activeWorkspaceId ?? "";

  const onChangeWorkspace = async (workspaceId: string): Promise<void> => {
    if (!workspaceId || workspaceId === selectedWorkspaceId) {
      return;
    }

    await switchWorkspaceMutation.mutateAsync({ workspaceId });
  };

  return (
    <div className={compact ? "w-[132px] sm:w-[172px]" : "min-w-[180px] max-w-[240px]"}>
      <label className="sr-only" htmlFor="workspace-switcher">
        {t("workspace.switcher.active")}
      </label>
      <Combobox
        id="workspace-switcher"
        className={
          compact
            ? "[&>button]:h-[32px] [&>button]:border-transparent [&>button]:bg-neutral-100 [&>button]:px-[10px] [&>button]:hover:border-neutral-300 [&>button]:hover:bg-neutral-0 [&>button]:focus-visible:ring-1 [&>button]:focus-visible:ring-neutral-300"
            : undefined
        }
        value={selectedWorkspaceId}
        onChange={(value) => {
          void onChangeWorkspace(value);
        }}
        disabled={workspaceQuery.isPending || switchWorkspaceMutation.isPending || options.length === 0}
        options={comboboxOptions}
        placeholder={t("workspace.switcher.loading")}
        searchPlaceholder={t("workspace.switcher.search")}
        emptyText={t("workspace.switcher.empty")}
        size={compact ? "sm" : "md"}
      />
      {!hideError && switchWorkspaceMutation.error ? (
        <p className="mt-1 text-xs text-error">{switchWorkspaceMutation.error.message}</p>
      ) : null}
    </div>
  );
}
