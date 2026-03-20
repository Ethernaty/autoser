"use client";

import type { Route } from "next";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { DataTable } from "@/design-system/primitives/data-table/data-table";
import type { DataTableColumn } from "@/design-system/primitives/data-table/data-table.types";
import { Badge, Button, FormActions, FormField, Input, Modal, Select } from "@/design-system/primitives";
import { PageLayout } from "@/design-system/patterns";
import {
  createEmployee,
  fetchEmployees,
  mvpQueryKeys,
  setEmployeeStatus,
  updateEmployee
} from "@/features/workspace/api/mvp-api";
import type { EmployeeRecord } from "@/features/workspace/types/mvp-types";

const PAGE_SIZE = 20;

type EmployeeForm = {
  email: string;
  password: string;
  role: string;
};

function defaultEmployeeForm(): EmployeeForm {
  return {
    email: "",
    password: "",
    role: "employee"
  };
}

function formatEmployeeName(email: string): string {
  const local = email.split("@")[0] ?? "";
  if (!local) {
    return "Employee";
  }

  return local
    .split(/[._-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatRoleLabel(role: string): string {
  return role.charAt(0).toUpperCase() + role.slice(1);
}

function roleTone(role: string): "primary" | "neutral" {
  return role === "owner" || role === "admin" ? "primary" : "neutral";
}

function EmployeeRowActions({
  onEdit,
  onToggle,
  isActive,
  disabled
}: {
  onEdit: () => void;
  onToggle: () => void;
  isActive: boolean;
  disabled: boolean;
}): JSX.Element {
  const [value, setValue] = useState("");

  return (
    <Select
      variant="subtle"
      className="h-8 w-[132px]"
      value={value}
      disabled={disabled}
      onClick={(event) => event.stopPropagation()}
      onChange={(event) => {
        const nextValue = event.target.value;
        setValue("");

        if (nextValue === "edit") {
          onEdit();
          return;
        }

        if (nextValue === "toggle") {
          onToggle();
        }
      }}
    >
      <option value="">Actions</option>
      <option value="edit">Edit</option>
      <option value="toggle">{isActive ? "Deactivate" : "Activate"}</option>
    </Select>
  );
}

export function EmployeesScreen(): JSX.Element {
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
    setError(null);
    setModalOpen(true);
  };

  const onOpenEdit = (employee: EmployeeRecord): void => {
    setEditingEmployee(employee);
    setForm({
      email: employee.email,
      password: "",
      role: employee.role
    });
    setError(null);
    setModalOpen(true);
  };

  const rows = employeesQuery.data?.items ?? [];
  const isStatusMutationPending = statusMutation.isPending;
  const columns = useMemo<DataTableColumn<EmployeeRecord>[]>(
    () => [
      {
        id: "employee",
        header: "Employee",
        minWidth: 320,
        cell: (row) => {
          const displayName = formatEmployeeName(row.email);
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
                <span className="block truncate font-semibold text-neutral-900">{displayName || "Employee"}</span>
                <span className="block truncate text-xs text-neutral-600">{row.email}</span>
              </span>
            </div>
          );
        }
      },
      {
        id: "role",
        header: "Role",
        minWidth: 120,
        cell: (row) => <Badge tone={roleTone(row.role)}>{formatRoleLabel(row.role)}</Badge>
      },
      {
        id: "status",
        header: "Status",
        minWidth: 120,
        cell: (row) => (row.is_active ? <Badge tone="success">Active</Badge> : <Badge tone="warning">Inactive</Badge>)
      },
      {
        id: "actions",
        header: "",
        minWidth: 140,
        align: "right",
        cell: (row) => (
          <div className="flex justify-end">
            <EmployeeRowActions
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
    [isStatusMutationPending, onOpenEdit, statusMutation]
  );

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    if (!form.email.trim() || !form.role.trim()) {
      setError("Email and role are required.");
      return;
    }
    if (!editingEmployee && form.password.trim().length < 8) {
      setError("Password must contain at least 8 characters.");
      return;
    }
    setError(null);

    if (editingEmployee) {
      await updateMutation.mutateAsync({
        employeeId: editingEmployee.employee_id,
        payload: {
          email: form.email.trim(),
          role: form.role,
          password: form.password.trim() ? form.password.trim() : undefined
        }
      });
    } else {
      await createMutation.mutateAsync({
        email: form.email.trim(),
        password: form.password.trim(),
        role: form.role
      });
    }

    setModalOpen(false);
    setEditingEmployee(null);
    setForm(defaultEmployeeForm());
  };

  return (
    <PageLayout
      title="Employees"
      subtitle="Workspace team directory and access roles"
      className="space-y-2"
      actions={
        <Button variant="primary" onClick={onOpenCreate}>
          Add employee
        </Button>
      }
    >
      <div className="space-y-1.5">
        <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search employees by name or email" />

        <DataTable
          columns={columns}
          rows={rows}
          getRowId={(row) => row.employee_id}
          onRowClick={onOpenEdit}
          loading={employeesQuery.isLoading}
          error={employeesQuery.error?.message}
          onRetry={() => void employeesQuery.refetch()}
          emptyTitle="No employees yet"
          emptyDescription="Add your first employee to start assigning work orders."
          emptyAction={
            <Button variant="primary" onClick={onOpenCreate}>
              Add employee
            </Button>
          }
          tableClassName="min-w-full"
          pagination={
            (employeesQuery.data?.total ?? 0) > 0
              ? {
                  page,
                  pageSize: PAGE_SIZE,
                  total: employeesQuery.data?.total ?? 0,
                  onPageChange: (nextPage) => {
                    setPage(nextPage);
                    updateUrlState({ q, page: nextPage });
                  }
                }
              : undefined
          }
        />
      </div>

      <Modal
        open={modalOpen}
        onOpenChange={setModalOpen}
        title={editingEmployee ? "Edit employee" : "Create employee"}
        description="Employee API uses canonical /employees endpoints"
        footer={
          <FormActions>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" form="employee-form" loading={createMutation.isPending || updateMutation.isPending}>
              {editingEmployee ? "Save" : "Create"}
            </Button>
          </FormActions>
        }
      >
        <form id="employee-form" className="space-y-2" onSubmit={(event) => void onSubmit(event)}>
          <FormField id="employee-email" label="Email" required>
            <Input
              id="employee-email"
              type="email"
              value={form.email}
              onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))}
            />
          </FormField>
          <FormField id="employee-role" label="Role" required>
            <select
              id="employee-role"
              className="h-5 w-full rounded-sm border border-neutral-300 bg-neutral-0 px-2 text-sm text-neutral-900"
              value={form.role}
              onChange={(event) => setForm((prev) => ({ ...prev, role: event.target.value }))}
            >
              <option value="owner">owner</option>
              <option value="admin">admin</option>
              <option value="manager">manager</option>
              <option value="employee">employee</option>
            </select>
          </FormField>
          <FormField id="employee-password" label={editingEmployee ? "Password (optional)" : "Password"} required={!editingEmployee}>
            <Input
              id="employee-password"
              type="password"
              value={form.password}
              onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
            />
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
