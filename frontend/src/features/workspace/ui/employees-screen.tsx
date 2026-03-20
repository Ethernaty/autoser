"use client";

import type { Route } from "next";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { DataTable } from "@/design-system/primitives/data-table/data-table";
import type { DataTableColumn } from "@/design-system/primitives/data-table/data-table.types";
import { Badge, Button, FormActions, FormField, Input, Modal } from "@/design-system/primitives";
import { PageLayout, Section, Toolbar } from "@/design-system/patterns";
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

  const updateUrlState = (next: { q: string; page: number }): void => {
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
  };

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

  const rows = employeesQuery.data?.items ?? [];
  const columns = useMemo<DataTableColumn<EmployeeRecord>[]>(
    () => [
      {
        id: "email",
        header: "Email",
        minWidth: 260,
        cell: (row) => <span className="font-medium text-neutral-900">{row.email}</span>
      },
      {
        id: "role",
        header: "Role",
        minWidth: 120,
        cell: (row) => <Badge tone="neutral">{row.role}</Badge>
      },
      {
        id: "active",
        header: "Status",
        minWidth: 140,
        cell: (row) => (row.is_active ? <Badge tone="success">Active</Badge> : <Badge tone="warning">Inactive</Badge>)
      },
      {
        id: "created",
        header: "Created",
        minWidth: 180,
        cell: (row) => new Date(row.created_at).toLocaleString()
      }
    ],
    []
  );

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
    <PageLayout title="Employees" subtitle="Workspace staff and roles">
      <Section>
        <Toolbar
          leading={
            <form
              className="flex items-center gap-1"
              onSubmit={(event) => {
                event.preventDefault();
                const nextQ = search.trim();
                setQ(nextQ);
                setPage(1);
                updateUrlState({ q: nextQ, page: 1 });
              }}
            >
              <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search employees" />
              <Button type="submit" variant="secondary">
                Search
              </Button>
            </form>
          }
          trailing={
            <Button variant="primary" onClick={onOpenCreate}>
              Add employee
            </Button>
          }
        />
      </Section>

      <Section>
        <DataTable
          columns={columns}
          rows={rows}
          getRowId={(row) => row.employee_id}
          loading={employeesQuery.isLoading}
          error={employeesQuery.error?.message}
          onRetry={() => void employeesQuery.refetch()}
          emptyTitle="No employees"
          emptyDescription="Create employee accounts to assign work orders."
          rowActions={[
            {
              id: "edit",
              label: "Edit",
              variant: "secondary",
              onClick: onOpenEdit
            },
            {
              id: "toggle",
              label: "Toggle active",
              onClick: (row) => {
                statusMutation.mutate({ employeeId: row.employee_id, isActive: !row.is_active });
              }
            }
          ]}
          pagination={{
            page,
            pageSize: PAGE_SIZE,
            total: employeesQuery.data?.total ?? 0,
            onPageChange: (nextPage) => {
              setPage(nextPage);
              updateUrlState({ q, page: nextPage });
            }
          }}
        />
      </Section>

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
