"use client";

import type { Route } from "next";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Eye, EyeOff, MoreHorizontal } from "lucide-react";
import { createPortal } from "react-dom";
import { type CSSProperties, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { DataTable } from "@/design-system/primitives/data-table/data-table";
import type { DataTableColumn } from "@/design-system/primitives/data-table/data-table.types";
import { Badge, Button, FormActions, FormField, Input, MobilePagination, Modal, Select } from "@/design-system/primitives";
import { PageLayout } from "@/design-system/patterns";
import {
  createEmployee,
  fetchEmployees,
  mvpQueryKeys,
  setEmployeeStatus,
  updateEmployee
} from "@/features/workspace/api/mvp-api";
import type { EmployeeRecord } from "@/features/workspace/types/mvp-types";
import { useI18n } from "@/shared/i18n";

const PAGE_SIZE = 20;

type EmployeeForm = {
  full_name: string;
  email: string;
  password: string;
  password_confirm: string;
  role: string;
  job_title: string;
  can_accept_payments: boolean;
};

function defaultEmployeeForm(): EmployeeForm {
  return {
    full_name: "",
    email: "",
    password: "",
    password_confirm: "",
    role: "employee",
    job_title: "",
    can_accept_payments: false
  };
}

function formatEmployeeName(fullName: string | null | undefined, email: string): string {
  const normalizedFullName = fullName?.trim();
  if (normalizedFullName) {
    return normalizedFullName;
  }
  const local = email.split("@")[0] ?? "";
  if (!local) {
    return "";
  }

  return local
    .split(/[._-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function roleTone(role: string): "primary" | "neutral" {
  return role === "owner" || role === "admin" ? "primary" : "neutral";
}

function EmployeeRowActions({
  onEdit,
  onToggle,
  isActive,
  disabled,
  t
}: {
  onEdit: () => void;
  onToggle: () => void;
  isActive: boolean;
  disabled: boolean;
  t: (key: string) => string;
}): JSX.Element {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [menuStyle, setMenuStyle] = useState<CSSProperties | null>(null);

  const updateMenuPosition = useCallback((): void => {
    const trigger = triggerRef.current;
    if (!trigger) {
      return;
    }

    const rect = trigger.getBoundingClientRect();
    const width = 180;
    const margin = 8;
    const spaceBelow = window.innerHeight - rect.bottom - margin;
    const showAbove = spaceBelow < 120 && rect.top > 140;

    setMenuStyle({
      position: "fixed",
      top: showAbove ? rect.top - 92 : rect.bottom + 6,
      left: Math.max(margin, rect.right - width),
      width,
      zIndex: 150
    });
  }, []);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onPointerDown = (event: MouseEvent): void => {
      if (!rootRef.current) {
        return;
      }
      const targetNode = event.target as Node;
      const clickInsideTrigger = rootRef.current.contains(targetNode);
      const clickInsideMenu = menuRef.current?.contains(targetNode) ?? false;
      if (!clickInsideTrigger && !clickInsideMenu) {
        setOpen(false);
      }
    };
    const onReposition = (): void => {
      updateMenuPosition();
    };
    updateMenuPosition();
    document.addEventListener("mousedown", onPointerDown);
    window.addEventListener("scroll", onReposition, true);
    window.addEventListener("resize", onReposition);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      window.removeEventListener("scroll", onReposition, true);
      window.removeEventListener("resize", onReposition);
    };
  }, [open, updateMenuPosition]);

  return (
    <div className="relative" ref={rootRef} onClick={(event) => event.stopPropagation()}>
      <button
        ref={triggerRef}
        type="button"
        className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-transparent text-neutral-600 transition-colors hover:border-neutral-300 hover:bg-neutral-50 hover:text-neutral-900"
        disabled={disabled}
        onClick={() => setOpen((prev) => !prev)}
        aria-label={t("common.actions")}
      >
        <MoreHorizontal className="h-4 w-4" />
      </button>
      {open && menuStyle
        ? createPortal(
            <div ref={menuRef} className="rounded-md border border-neutral-200 bg-neutral-0 p-1 shadow-md" style={menuStyle}>
              <button
                type="button"
                className="w-full rounded-md px-2 py-1.5 text-left text-sm text-neutral-800 hover:bg-neutral-100"
                onClick={() => {
                  setOpen(false);
                  onEdit();
                }}
              >
                {t("common.edit")}
              </button>
              <button
                type="button"
                className="w-full rounded-md px-2 py-1.5 text-left text-sm text-neutral-800 hover:bg-neutral-100"
                onClick={() => {
                  setOpen(false);
                  onToggle();
                }}
              >
                {isActive ? t("employees.deactivate") : t("employees.activate")}
              </button>
            </div>,
            document.body
          )
        : null}
    </div>
  );
}

export function EmployeesScreen(): JSX.Element {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const initialQ = searchParams.get("q") ?? "";
  const initialPageRaw = Number(searchParams.get("page") ?? "1");
  const initialPage = Number.isFinite(initialPageRaw) && initialPageRaw > 0 ? initialPageRaw : 1;

  const [q, setQ] = useState(initialQ);
  const [search, setSearch] = useState(initialQ);
  const [page, setPage] = useState(initialPage);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<EmployeeRecord | null>(null);
  const [form, setForm] = useState<EmployeeForm>(defaultEmployeeForm());
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirm, setShowPasswordConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const nextQ = searchParams.get("q") ?? "";
    const nextPageRaw = Number(searchParams.get("page") ?? "1");
    const nextPage = Number.isFinite(nextPageRaw) && nextPageRaw > 0 ? nextPageRaw : 1;
    setQ(nextQ);
    setSearch(nextQ);
    setPage(nextPage);
  }, [searchParams]);

  const updateUrlState = useCallback(
    (next: { q: string; page: number }): void => {
      const params = new URLSearchParams(searchParams.toString());
      if (next.q) {
        params.set("q", next.q);
      } else {
        params.delete("q");
      }
      if (next.page > 1) {
        params.set("page", String(next.page));
      } else {
        params.delete("page");
      }
      const queryString = params.toString();
      const nextHref = queryString ? `${pathname}?${queryString}` : pathname;
      router.replace(nextHref as Route, { scroll: false });
    },
    [pathname, router, searchParams]
  );

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      const nextQ = search.trim();
      if (nextQ === q) {
        return;
      }
      setQ(nextQ);
      setPage(1);
      updateUrlState({ q: nextQ, page: 1 });
    }, 250);

    return () => {
      window.clearTimeout(timeout);
    };
  }, [q, search, updateUrlState]);

  const offset = (page - 1) * PAGE_SIZE;
  const employeesQuery = useQuery({
    queryKey: mvpQueryKeys.employees(q, "", PAGE_SIZE, offset),
    queryFn: () => fetchEmployees({ q, limit: PAGE_SIZE, offset }),
    placeholderData: keepPreviousData
  });

  const createMutation = useMutation({
    mutationFn: createEmployee,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["employees"] });
    }
  });

  const updateMutation = useMutation({
    mutationFn: ({ employeeId, payload }: { employeeId: string; payload: Parameters<typeof updateEmployee>[1] }) =>
      updateEmployee(employeeId, payload),
    onSuccess: (_, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["employees"] });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.employee(variables.employeeId) });
    }
  });

  const statusMutation = useMutation({
    mutationFn: ({ employeeId, isActive }: { employeeId: string; isActive: boolean }) =>
      setEmployeeStatus(employeeId, isActive),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["employees"] });
    }
  });

  const onOpenCreate = (): void => {
    setEditingEmployee(null);
    setForm(defaultEmployeeForm());
    setShowPassword(false);
    setShowPasswordConfirm(false);
    setError(null);
    setModalOpen(true);
  };

  const onOpenEdit = useCallback((employee: EmployeeRecord): void => {
    setEditingEmployee(employee);
    setForm({
      full_name: employee.full_name ?? "",
      email: employee.email,
      password: "",
      password_confirm: "",
      role: employee.role,
      job_title: employee.job_title ?? "",
      can_accept_payments: employee.can_accept_payments
    });
    setShowPassword(false);
    setShowPasswordConfirm(false);
    setError(null);
    setModalOpen(true);
  }, []);

  const rows = employeesQuery.data?.items ?? [];
  const totalEmployees = employeesQuery.data?.total ?? 0;
  const isStatusMutationPending = statusMutation.isPending;
  const columns = useMemo<DataTableColumn<EmployeeRecord>[]>(
    () => [
      {
        id: "employee",
        header: t("employees.table.employee"),
        minWidth: 320,
        cell: (row) => {
          const displayName = formatEmployeeName(row.full_name, row.email);
          const initials = displayName
            .split(" ")
            .filter(Boolean)
            .slice(0, 2)
            .map((part) => part.charAt(0))
            .join("")
            .toUpperCase();

          return (
            <div className="flex items-center gap-2">
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-neutral-200 text-[11px] font-semibold text-neutral-700">
                {initials || "E"}
              </span>
              <span className="min-w-0">
                <span className="block truncate font-semibold text-neutral-900">{displayName || t("employees.default_name")}</span>
                <span className="block truncate text-xs text-neutral-600">{row.email}</span>
              </span>
            </div>
          );
        }
      },
      {
        id: "role",
        header: t("employees.table.role"),
        minWidth: 120,
        cell: (row) => (
          <div>
            {row.job_title ? <p className="mb-1 text-xs text-neutral-600">{row.job_title}</p> : null}
            <Badge tone={roleTone(row.role)}>{t(`employees.role.${row.role}`)}</Badge>
          </div>
        )
      },
      {
        id: "status",
        header: t("common.status"),
        minWidth: 120,
        cell: (row) => (row.is_active ? <Badge tone="success">{t("employees.status.active")}</Badge> : <Badge tone="warning">{t("employees.status.inactive")}</Badge>)
      },
      {
        id: "actions",
        header: "",
        minWidth: 140,
        align: "right",
        cell: (row) => (
          <div className="flex justify-end">
            <EmployeeRowActions
              t={t}
              disabled={isStatusMutationPending}
              isActive={row.is_active}
              onEdit={() => onOpenEdit(row)}
              onToggle={() => {
                statusMutation.mutate({ employeeId: row.employee_id, isActive: !row.is_active });
              }}
            />
          </div>
        )
      }
    ],
    [isStatusMutationPending, onOpenEdit, statusMutation, t]
  );

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    if (!form.full_name.trim() || !form.role.trim()) {
      setError(t("employees.form.error.required"));
      return;
    }
    const normalizedPassword = form.password.trim();
    if (!editingEmployee && normalizedPassword.length < 8) {
      setError(t("employees.form.error.password"));
      return;
    }
    if ((editingEmployee && normalizedPassword.length > 0) || !editingEmployee) {
      if (normalizedPassword !== form.password_confirm.trim()) {
        setError(t("employees.form.error.password_mismatch"));
        return;
      }
    }

    const normalizedEmail = form.email.trim();
    if (normalizedEmail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
      setError(t("employees.form.error.email"));
      return;
    }

    setError(null);

    if (editingEmployee) {
      await updateMutation.mutateAsync({
        employeeId: editingEmployee.employee_id,
        payload: {
          full_name: form.full_name.trim(),
          email: normalizedEmail || undefined,
          role: form.role,
          job_title: form.job_title.trim() || null,
          can_accept_payments: form.can_accept_payments,
          password: normalizedPassword ? normalizedPassword : undefined
        }
      });
    } else {
      await createMutation.mutateAsync({
        full_name: form.full_name.trim(),
        email: normalizedEmail || null,
        password: normalizedPassword,
        role: form.role,
        job_title: form.job_title.trim() || null,
        can_accept_payments: form.can_accept_payments
      });
    }

    setModalOpen(false);
    setEditingEmployee(null);
    setForm(defaultEmployeeForm());
  };

  return (
    <PageLayout
      title={t("employees.title")}
      subtitle={t("employees.subtitle")}
      className="space-y-2"
      actions={
        <Button variant="primary" onClick={onOpenCreate}>
          {t("employees.add")}
        </Button>
      }
    >
      <div className="space-y-1.5">
        <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={t("employees.search_placeholder")} />

        <div className="space-y-1.5 md:hidden">
          {employeesQuery.isLoading ? (
            Array.from({ length: 4 }).map((_, index) => (
              <div key={`employee-skeleton-${index}`} className="h-[102px] rounded-md border border-neutral-200 bg-neutral-0 p-2.5">
                <div className="h-3 w-3/5 rounded bg-neutral-100" />
                <div className="mt-2 h-2.5 w-4/5 rounded bg-neutral-100" />
              </div>
            ))
          ) : employeesQuery.error ? (
            <div className="rounded-md border border-error/30 bg-error/5 p-2.5">
              <p className="text-sm text-error">{employeesQuery.error.message}</p>
              <Button className="mt-2" size="sm" variant="secondary" onClick={() => void employeesQuery.refetch()}>
                {t("datatable.retry")}
              </Button>
            </div>
          ) : rows.length ? (
            rows.map((employee) => {
              const displayName = formatEmployeeName(employee.full_name, employee.email) || t("employees.default_name");
              return (
                <article
                  key={employee.employee_id}
                  className="w-full rounded-md border border-neutral-200 bg-neutral-0 p-2.5 transition-colors hover:border-neutral-300 hover:bg-neutral-50"
                >
                  <button
                    type="button"
                    onClick={() => onOpenEdit(employee)}
                    className="w-full text-left"
                  >
                    <p className="truncate text-sm font-semibold text-neutral-900">{displayName}</p>
                    <p className="mt-1 truncate text-xs text-neutral-600">{employee.email}</p>
                    {employee.job_title ? <p className="mt-1 truncate text-xs text-neutral-600">{employee.job_title}</p> : null}
                    <div className="mt-2 flex flex-wrap items-center gap-1.5">
                      <Badge tone={roleTone(employee.role)}>{t(`employees.role.${employee.role}`)}</Badge>
                      {employee.is_active ? (
                        <Badge tone="success">{t("employees.status.active")}</Badge>
                      ) : (
                        <Badge tone="warning">{t("employees.status.inactive")}</Badge>
                      )}
                    </div>
                  </button>
                  <div className="mt-2 flex gap-1.5">
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      onClick={() => onOpenEdit(employee)}
                    >
                      {t("common.edit")}
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      disabled={isStatusMutationPending}
                      onClick={() => {
                        statusMutation.mutate({ employeeId: employee.employee_id, isActive: !employee.is_active });
                      }}
                    >
                      {employee.is_active ? t("employees.deactivate") : t("employees.activate")}
                    </Button>
                  </div>
                </article>
              );
            })
          ) : (
            <div className="rounded-md border border-neutral-200 bg-neutral-0 p-3 text-center">
              <p className="text-sm font-semibold text-neutral-900">{t("employees.empty.title")}</p>
              <p className="mt-1 text-xs text-neutral-600">{t("employees.empty.description")}</p>
              <Button className="mt-2" variant="primary" onClick={onOpenCreate}>
                {t("employees.add")}
              </Button>
            </div>
          )}
          <MobilePagination
            page={page}
            pageSize={PAGE_SIZE}
            total={totalEmployees}
            onPageChange={(nextPage) => {
              setPage(nextPage);
              updateUrlState({ q, page: nextPage });
            }}
            label="{page}/{total}"
            prevLabel={t("datatable.pagination.prev")}
            nextLabel={t("datatable.pagination.next")}
          />
        </div>

        <div className="hidden md:block">
          <DataTable
            columns={columns}
            rows={rows}
            getRowId={(row) => row.employee_id}
            onRowClick={onOpenEdit}
            loading={employeesQuery.isLoading}
            error={employeesQuery.error?.message}
            onRetry={() => void employeesQuery.refetch()}
            emptyTitle={t("employees.empty.title")}
            emptyDescription={t("employees.empty.description")}
            emptyAction={
              <Button variant="primary" onClick={onOpenCreate}>
                {t("employees.add")}
              </Button>
            }
            tableClassName="min-w-full"
            pagination={
              totalEmployees > 0
                ? {
                    page,
                    pageSize: PAGE_SIZE,
                    total: totalEmployees,
                    onPageChange: (nextPage) => {
                      setPage(nextPage);
                      updateUrlState({ q, page: nextPage });
                    }
                  }
                : undefined
            }
          />
        </div>
      </div>

      <Modal
        open={modalOpen}
        onOpenChange={setModalOpen}
        title={editingEmployee ? t("employees.modal.edit_title") : t("employees.modal.create_title")}
        description={t("employees.modal.description")}
        footer={
          <FormActions>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" form="employee-form" loading={createMutation.isPending || updateMutation.isPending}>
              {editingEmployee ? t("common.save") : t("common.create")}
            </Button>
          </FormActions>
        }
      >
        <form id="employee-form" className="space-y-2" onSubmit={(event) => void onSubmit(event)}>
          <FormField id="employee-full-name" label={t("employees.form.full_name")} required>
            <Input
              id="employee-full-name"
              value={form.full_name}
              onChange={(event) => setForm((prev) => ({ ...prev, full_name: event.target.value }))}
            />
          </FormField>
          <FormField id="employee-email" label={t("employees.form.email_optional")}>
            <Input
              id="employee-email"
              type="email"
              value={form.email}
              placeholder={t("employees.form.email_optional_placeholder")}
              onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))}
            />
          </FormField>
          <FormField id="employee-job-title" label={t("employees.form.position")}>
            <Input id="employee-job-title" value={form.job_title} placeholder={t("employees.form.position_placeholder")} onChange={(event) => setForm((prev) => ({ ...prev, job_title: event.target.value }))} />
          </FormField>
          <FormField id="employee-role" label={t("employees.form.access_role")} required>
            <Select id="employee-role" value={form.role} onChange={(event) => setForm((prev) => ({ ...prev, role: event.target.value }))}>
              <option value="owner">{t("employees.role.owner")}</option>
              <option value="admin">{t("employees.role.admin")}</option>
              <option value="manager">{t("employees.role.manager")}</option>
              <option value="employee">{t("employees.role.employee")}</option>
            </Select>
          </FormField>
          <label className="flex items-center gap-2 text-sm text-neutral-700">
            <input type="checkbox" checked={form.can_accept_payments} onChange={(event) => setForm((prev) => ({ ...prev, can_accept_payments: event.target.checked }))} />
            {t("employees.form.can_accept_payments")}
          </label>
          <FormField id="employee-password" label={editingEmployee ? t("employees.form.password_optional") : t("common.password")} required={!editingEmployee}>
            <div className="relative">
              <Input
                id="employee-password"
                type={showPassword ? "text" : "password"}
                value={form.password}
                onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
              />
              <button
                type="button"
                className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-neutral-800"
                onClick={() => setShowPassword((prev) => !prev)}
                aria-label={showPassword ? t("employees.form.hide_password") : t("employees.form.show_password")}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </FormField>
          <FormField
            id="employee-password-confirm"
            label={t("employees.form.password_confirm")}
            required={!editingEmployee || Boolean(form.password.trim())}
          >
            <div className="relative">
              <Input
                id="employee-password-confirm"
                type={showPasswordConfirm ? "text" : "password"}
                value={form.password_confirm}
                onChange={(event) => setForm((prev) => ({ ...prev, password_confirm: event.target.value }))}
              />
              <button
                type="button"
                className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-neutral-800"
                onClick={() => setShowPasswordConfirm((prev) => !prev)}
                aria-label={showPasswordConfirm ? t("employees.form.hide_password") : t("employees.form.show_password")}
              >
                {showPasswordConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </FormField>
          {error ? <p className="text-sm text-error">{error}</p> : null}
          {createMutation.error ? <p className="text-sm text-error">{createMutation.error.message}</p> : null}
          {updateMutation.error ? <p className="text-sm text-error">{updateMutation.error.message}</p> : null}
          {statusMutation.error ? <p className="text-sm text-error">{statusMutation.error.message}</p> : null}
        </form>
      </Modal>
    </PageLayout>
  );
}
