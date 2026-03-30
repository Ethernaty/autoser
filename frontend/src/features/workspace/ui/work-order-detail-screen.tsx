"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ROUTES } from "@/core/config/routes";
import { cn } from "@/core/lib/utils";
import {
  Badge,
  Button,
  Card,
  Combobox,
  FormActions,
  FormField,
  Input,
  Modal,
  Select,
  Textarea
} from "@/design-system/primitives";
import { PageLayout, Section, StateBoundary } from "@/design-system/patterns";
import { isApiClientError } from "@/shared/api/client";
import {
  addWorkOrderTimelineComment,
  addWorkOrderLine,
  assignWorkOrder,
  closeWorkOrder,
  createWorkOrderPayment,
  deleteWorkOrderLine,
  fetchEmployees,
  fetchVehicle,
  fetchWorkOrder,
  fetchWorkOrderLines,
  fetchWorkOrderPayments,
  fetchWorkOrderTimeline,
  mvpQueryKeys,
  setWorkOrderStatus,
  updateWorkOrderLine
} from "@/features/workspace/api/mvp-api";
import type { WorkOrderOrderLine, WorkOrderPaymentState, WorkOrderStatus } from "@/features/workspace/types/mvp-types";
import { useI18n } from "@/shared/i18n";

const EMPLOYEE_LOOKUP_LIMIT = 50;

function formatMoney(value: string): string {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return value;
  }
  return parsed.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function statusLabel(status: WorkOrderStatus, t: (key: string) => string): string {
  if (status === "in_progress") {
    return t("dashboard.status.in_progress");
  }
  if (status === "completed_unpaid") {
    return t("dashboard.status.completed_unpaid");
  }
  if (status === "completed_paid") {
    return t("dashboard.status.completed_paid");
  }
  if (status === "cancelled") {
    return t("dashboard.status.cancelled");
  }
  return t("dashboard.status.new");
}

function statusTone(status: WorkOrderStatus): "neutral" | "warning" | "success" | "error" {
  if (status === "in_progress" || status === "completed_unpaid") {
    return "warning";
  }
  if (status === "completed_paid") {
    return "success";
  }
  if (status === "cancelled") {
    return "error";
  }
  return "neutral";
}

function paymentStateLabel(state: WorkOrderPaymentState, t: (key: string) => string): string {
  if (state === "paid") {
    return t("work_orders.payment_state.paid");
  }
  if (state === "partial") {
    return t("work_orders.payment_state.partial");
  }
  return t("work_orders.payment_state.unpaid");
}

function paymentStateTone(state: WorkOrderPaymentState): "neutral" | "warning" | "success" {
  if (state === "paid") {
    return "success";
  }
  if (state === "partial") {
    return "warning";
  }
  return "neutral";
}

type TimelineKind = "created" | "status" | "payment" | "cancelled" | "amount" | "lines" | "assignee" | "vehicle" | "comment" | "other";

type TimelinePresentation = {
  kind: TimelineKind;
  typeLabel: string;
  title: string;
  details: string | null;
  statusFrom: WorkOrderStatus | null;
  statusTo: WorkOrderStatus | null;
};

function parseWorkOrderStatus(value: string): WorkOrderStatus | null {
  if (["new", "in_progress", "completed_unpaid", "completed_paid", "cancelled"].includes(value)) {
    return value as WorkOrderStatus;
  }
  return null;
}

function statusFromMessage(message: string): { from: WorkOrderStatus; to: WorkOrderStatus } | null {
  const match = message.match(/from\s+([a-z_]+)\s+to\s+([a-z_]+)/i);
  if (!match) {
    return null;
  }
  const from = parseWorkOrderStatus(match[1]);
  const to = parseWorkOrderStatus(match[2]);
  if (!from || !to) {
    return null;
  }
  return { from, to };
}

function eventTypeLabel(kind: TimelineKind, t: (key: string) => string): string {
  if (kind === "created") return t("work_order_timeline.type.created");
  if (kind === "status") return t("work_order_timeline.type.status");
  if (kind === "payment") return t("work_order_timeline.type.payment");
  if (kind === "cancelled") return t("work_order_timeline.type.cancelled");
  if (kind === "amount") return t("work_order_timeline.type.amount");
  if (kind === "lines") return t("work_order_timeline.type.lines");
  if (kind === "assignee") return t("work_order_timeline.type.assignee");
  if (kind === "vehicle") return t("work_order_timeline.type.vehicle");
  if (kind === "comment") return t("work_order_timeline.type.comment");
  return t("work_order_timeline.type.other");
}

function timelinePresentation(
  item: { action: string; message: string },
  t: (key: string, values?: Record<string, string | number>) => string
): TimelinePresentation {
  if (item.action === "work_order_created") {
    return {
      kind: "created",
      typeLabel: eventTypeLabel("created", t),
      title: t("work_order_timeline.created"),
      details: null,
      statusFrom: null,
      statusTo: null
    };
  }
  if (item.action === "work_order_cancelled") {
    return {
      kind: "cancelled",
      typeLabel: eventTypeLabel("cancelled", t),
      title: t("work_order_timeline.cancelled"),
      details: null,
      statusFrom: null,
      statusTo: null
    };
  }
  if (item.action === "work_order_status_changed") {
    const transition = statusFromMessage(item.message);
    return {
      kind: "status",
      typeLabel: eventTypeLabel("status", t),
      title: t("work_order_timeline.status_changed_generic"),
      details: transition ? null : item.message,
      statusFrom: transition?.from ?? null,
      statusTo: transition?.to ?? null
    };
  }
  if (item.action === "work_order_total_amount_changed") {
    const match = item.message.match(/from\s+([0-9.]+)\s+to\s+([0-9.]+)/i);
    return {
      kind: "amount",
      typeLabel: eventTypeLabel("amount", t),
      title: t("work_order_timeline.total_changed_generic"),
      details: match ? `${formatMoney(match[1])} -> ${formatMoney(match[2])}` : item.message,
      statusFrom: null,
      statusTo: null
    };
  }
  if (item.action === "work_order_lines_changed") {
    let title = t("work_order_timeline.lines_changed_generic");
    if (item.message.startsWith("Added line")) {
      title = t("work_order_timeline.lines_added");
    } else if (item.message.startsWith("Updated line")) {
      title = t("work_order_timeline.lines_updated");
    } else if (item.message.startsWith("Removed line")) {
      title = t("work_order_timeline.lines_removed");
    }
    return {
      kind: "lines",
      typeLabel: eventTypeLabel("lines", t),
      title,
      details: null,
      statusFrom: null,
      statusTo: null
    };
  }
  if (item.action === "work_order_payment_recorded") {
    return {
      kind: "payment",
      typeLabel: eventTypeLabel("payment", t),
      title: t("work_order_timeline.payment_recorded"),
      details: null,
      statusFrom: null,
      statusTo: null
    };
  }
  if (item.action === "work_order_assignee_changed") {
    return {
      kind: "assignee",
      typeLabel: eventTypeLabel("assignee", t),
      title: t("work_order_timeline.assignee_changed"),
      details: null,
      statusFrom: null,
      statusTo: null
    };
  }
  if (item.action === "work_order_vehicle_changed") {
    return {
      kind: "vehicle",
      typeLabel: eventTypeLabel("vehicle", t),
      title: t("work_order_timeline.vehicle_changed"),
      details: null,
      statusFrom: null,
      statusTo: null
    };
  }
  if (item.action === "work_order_comment_added") {
    return {
      kind: "comment",
      typeLabel: eventTypeLabel("comment", t),
      title: t("work_order_timeline.comment_added"),
      details: item.message,
      statusFrom: null,
      statusTo: null
    };
  }

  return {
    kind: "other",
    typeLabel: eventTypeLabel("other", t),
    title: item.message,
    details: null,
    statusFrom: null,
    statusTo: null
  };
}

function timelineKindStyles(kind: TimelineKind): {
  dotClass: string;
  chipClass: string;
} {
  if (kind === "created") return { dotClass: "bg-primary", chipClass: "bg-primary/10 text-primary" };
  if (kind === "status") return { dotClass: "bg-warning", chipClass: "bg-warning/10 text-warning" };
  if (kind === "payment") return { dotClass: "bg-success", chipClass: "bg-success/10 text-success" };
  if (kind === "cancelled") return { dotClass: "bg-error", chipClass: "bg-error/10 text-error" };
  if (kind === "amount") return { dotClass: "bg-amber-500", chipClass: "bg-amber-100 text-amber-700" };
  if (kind === "lines") return { dotClass: "bg-indigo-500", chipClass: "bg-indigo-100 text-indigo-700" };
  if (kind === "assignee") return { dotClass: "bg-cyan-500", chipClass: "bg-cyan-100 text-cyan-700" };
  if (kind === "vehicle") return { dotClass: "bg-violet-500", chipClass: "bg-violet-100 text-violet-700" };
  if (kind === "comment") return { dotClass: "bg-sky-500", chipClass: "bg-sky-100 text-sky-700" };
  return { dotClass: "bg-neutral-400", chipClass: "bg-neutral-200 text-neutral-700" };
}

function formatRelativeTime(value: string, locale: "ru" | "en"): string {
  const date = new Date(value);
  const diffMs = date.getTime() - Date.now();
  const absSeconds = Math.abs(Math.round(diffMs / 1000));

  const rtf = new Intl.RelativeTimeFormat(locale === "ru" ? "ru-RU" : "en-US", { numeric: "auto" });
  if (absSeconds < 60) return rtf.format(Math.round(diffMs / 1000), "second");
  if (absSeconds < 3600) return rtf.format(Math.round(diffMs / (60 * 1000)), "minute");
  if (absSeconds < 86400) return rtf.format(Math.round(diffMs / (60 * 60 * 1000)), "hour");
  return rtf.format(Math.round(diffMs / (24 * 60 * 60 * 1000)), "day");
}

function resolveWorkOrderActionError(error: unknown, t: (key: string) => string): string {
  if (isApiClientError(error)) {
    if (error.code === "work_order_closed") {
      return t("work_order_detail.error.lines_locked");
    }
    if (error.code === "cannot_mark_completed_paid") {
      return t("work_order_detail.error.cannot_mark_completed_paid");
    }
    if (error.code === "cannot_cancel_paid_order") {
      return t("work_order_detail.error.cannot_cancel_paid_order");
    }
    if (error.code === "payment_not_allowed_for_cancelled") {
      return t("work_order_detail.error.payment_not_allowed_for_cancelled");
    }
    if (error.code === "total_below_paid_amount") {
      return t("work_order_detail.error.total_below_paid_amount");
    }
    if (error.code === "completed_paid_payment_mismatch") {
      return t("work_order_detail.error.completed_paid_payment_mismatch");
    }
    return error.message;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return t("state.error.title");
}

function DetailMetric({
  label,
  value,
  accent = false
}: {
  label: string;
  value: React.ReactNode;
  accent?: boolean;
}): JSX.Element {
  return (
    <Card className={cn("border-neutral-200 bg-neutral-0 p-2", accent && "border-primary/20 bg-primary/5")}>
      <p className="text-[11px] font-semibold uppercase tracking-wide text-neutral-600">{label}</p>
      <div className="mt-1 text-2xl font-semibold leading-none text-neutral-950">{value}</div>
    </Card>
  );
}

export function WorkOrderDetailScreen({ workOrderId }: { workOrderId: string }): JSX.Element {
  const { t, locale } = useI18n();
  const queryClient = useQueryClient();
  const [documentPreviewOpen, setDocumentPreviewOpen] = useState(false);
  const [documentFormat, setDocumentFormat] = useState<"pdf" | "html" | "docx">("pdf");
  const [documentPreviewHtml, setDocumentPreviewHtml] = useState("");
  const [documentPreviewLoading, setDocumentPreviewLoading] = useState(false);
  const [documentPreviewError, setDocumentPreviewError] = useState<string | null>(null);
  const [documentLoading, setDocumentLoading] = useState<null | "pdf" | "html" | "docx">(null);
  const [lineModalOpen, setLineModalOpen] = useState(false);
  const [editLineModalOpen, setEditLineModalOpen] = useState(false);
  const [editingLine, setEditingLine] = useState<WorkOrderOrderLine | null>(null);
  const [paymentModalOpen, setPaymentModalOpen] = useState(false);
  const [lineDraft, setLineDraft] = useState({
    line_type: "labor" as "labor" | "part" | "misc",
    name: "",
    quantity: "1",
    unit_price: "",
    comment: ""
  });
  const [editLineDraft, setEditLineDraft] = useState({
    line_type: "labor" as "labor" | "part" | "misc",
    name: "",
    quantity: "1",
    unit_price: "",
    comment: ""
  });
  const [paymentDraft, setPaymentDraft] = useState({
    amount: "",
    method: "cash" as "cash" | "card" | "transfer" | "other",
    comment: ""
  });
  const [lineError, setLineError] = useState<string | null>(null);
  const [editLineError, setEditLineError] = useState<string | null>(null);
  const [lineActionError, setLineActionError] = useState<string | null>(null);
  const [statusActionError, setStatusActionError] = useState<string | null>(null);
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const [timelineCommentDraft, setTimelineCommentDraft] = useState("");
  const [timelineCommentError, setTimelineCommentError] = useState<string | null>(null);

  const workOrderQuery = useQuery({
    queryKey: mvpQueryKeys.workOrder(workOrderId),
    queryFn: () => fetchWorkOrder(workOrderId)
  });

  const linesQuery = useQuery({
    queryKey: mvpQueryKeys.workOrderLines(workOrderId),
    queryFn: () => fetchWorkOrderLines(workOrderId)
  });

  const paymentsQuery = useQuery({
    queryKey: mvpQueryKeys.workOrderPayments(workOrderId),
    queryFn: () => fetchWorkOrderPayments(workOrderId)
  });

  const timelineQuery = useQuery({
    queryKey: mvpQueryKeys.workOrderTimeline(workOrderId, 100, 0),
    queryFn: () => fetchWorkOrderTimeline(workOrderId, { limit: 100, offset: 0 })
  });

  const employeesQuery = useQuery({
    queryKey: mvpQueryKeys.employees("", "", EMPLOYEE_LOOKUP_LIMIT, 0),
    queryFn: () => fetchEmployees({ limit: EMPLOYEE_LOOKUP_LIMIT, offset: 0 })
  });

  const employeeById = useMemo(() => {
    const map = new Map<string, string>();
    (employeesQuery.data?.items ?? []).forEach((employee) => {
      const label = employee.full_name?.trim() ? `${employee.full_name} (${employee.role})` : `${employee.email} (${employee.role})`;
      map.set(employee.employee_id, label);
    });
    return map;
  }, [employeesQuery.data?.items]);

  const attachedVehicleQuery = useQuery({
    queryKey: mvpQueryKeys.vehicle(workOrderQuery.data?.vehicle_id ?? ""),
    queryFn: () => fetchVehicle(workOrderQuery.data!.vehicle_id!),
    enabled: Boolean(workOrderQuery.data?.vehicle_id)
  });

  const statusMutation = useMutation({
    mutationFn: (status: WorkOrderStatus) => setWorkOrderStatus(workOrderId, status),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrder(workOrderId) });
      void queryClient.invalidateQueries({ queryKey: ["work-orders"] });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrderTimeline(workOrderId, 100, 0) });
    }
  });

  const closeMutation = useMutation({
    mutationFn: () => closeWorkOrder(workOrderId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrder(workOrderId) });
      void queryClient.invalidateQueries({ queryKey: ["work-orders"] });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrderTimeline(workOrderId, 100, 0) });
    }
  });

  const assignMutation = useMutation({
    mutationFn: (employeeId: string | null) => assignWorkOrder(workOrderId, employeeId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrder(workOrderId) });
      void queryClient.invalidateQueries({ queryKey: ["work-orders"] });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrderTimeline(workOrderId, 100, 0) });
    }
  });

  const addLineMutation = useMutation({
    mutationFn: addWorkOrderLine.bind(null, workOrderId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrderLines(workOrderId) });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrder(workOrderId) });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrderTimeline(workOrderId, 100, 0) });
    }
  });

  const updateLineMutation = useMutation({
    mutationFn: ({
      lineId,
      payload
    }: {
      lineId: string;
      payload: {
        line_type?: "labor" | "part" | "misc";
        name?: string;
        quantity?: number;
        unit_price?: number;
        comment?: string | null;
      };
    }) => updateWorkOrderLine(workOrderId, lineId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrderLines(workOrderId) });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrder(workOrderId) });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrderTimeline(workOrderId, 100, 0) });
    }
  });

  const deleteLineMutation = useMutation({
    mutationFn: (lineId: string) => deleteWorkOrderLine(workOrderId, lineId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrderLines(workOrderId) });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrder(workOrderId) });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrderTimeline(workOrderId, 100, 0) });
    }
  });

  const addPaymentMutation = useMutation({
    mutationFn: createWorkOrderPayment.bind(null, workOrderId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrderPayments(workOrderId) });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrder(workOrderId) });
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrderTimeline(workOrderId, 100, 0) });
    }
  });

  const addTimelineCommentMutation = useMutation({
    mutationFn: (comment: string) => addWorkOrderTimelineComment(workOrderId, comment),
    onSuccess: () => {
      setTimelineCommentDraft("");
      setTimelineCommentError(null);
      void queryClient.invalidateQueries({ queryKey: mvpQueryKeys.workOrderTimeline(workOrderId, 100, 0) });
    }
  });

  const openEditLineModal = (line: WorkOrderOrderLine): void => {
    setEditingLine(line);
    setEditLineDraft({
      line_type: line.line_type,
      name: line.name,
      quantity: String(line.quantity),
      unit_price: String(line.unit_price),
      comment: line.comment ?? ""
    });
    setEditLineError(null);
    setEditLineModalOpen(true);
  };

  const employeeOptions = useMemo(
    () => [
      { value: "__unassigned", label: t("work_orders.unassigned"), keywords: [t("work_orders.unassigned")] },
      ...(employeesQuery.data?.items ?? []).map((employee) => ({
        value: employee.employee_id,
        label: employee.full_name?.trim() ? `${employee.full_name} (${employee.role})` : `${employee.email} (${employee.role})`,
        keywords: [employee.full_name ?? "", employee.email, employee.role]
      }))
    ],
    [employeesQuery.data?.items, t]
  );

  const currentAssigneeLabel =
    workOrderQuery.data?.assigned_employee_id && employeeById.get(workOrderQuery.data.assigned_employee_id)
      ? employeeById.get(workOrderQuery.data.assigned_employee_id)
      : workOrderQuery.data?.assigned_employee_id
        ? workOrderQuery.data.assigned_employee_id
        : t("work_orders.unassigned");

  const availableStatusTransitions = useMemo((): WorkOrderStatus[] => {
    const current = workOrderQuery.data?.status;
    if (!current) {
      return [];
    }
    if (current === "new") {
      return ["in_progress", "cancelled"];
    }
    if (current === "in_progress") {
      return ["completed_unpaid", "completed_paid", "cancelled"];
    }
    if (current === "completed_unpaid") {
      return ["completed_paid", "cancelled"];
    }
    if (current === "completed_paid") {
      return ["cancelled"];
    }
    return [];
  }, [workOrderQuery.data?.status]);

  const areLinesEditable = useMemo(() => {
    const status = workOrderQuery.data?.status;
    return status !== "completed_unpaid" && status !== "completed_paid" && status !== "cancelled";
  }, [workOrderQuery.data?.status]);

  const remainingAmountValue = useMemo(() => Number(workOrderQuery.data?.remaining_amount ?? "0"), [workOrderQuery.data?.remaining_amount]);
  const paidAmountValue = useMemo(() => Number(workOrderQuery.data?.paid_amount ?? "0"), [workOrderQuery.data?.paid_amount]);
  const canSetCompletedPaid = remainingAmountValue <= 0;
  const canSetCompletedUnpaid = remainingAmountValue > 0;
  const canCancelOrder = paidAmountValue <= 0;
  const canAddPayment = workOrderQuery.data?.status !== "cancelled";

  const runStatusTransition = async (status: WorkOrderStatus): Promise<void> => {
    setStatusActionError(null);
    try {
      await statusMutation.mutateAsync(status);
    } catch (error) {
      setStatusActionError(resolveWorkOrderActionError(error, t));
    }
  };

  const runCloseOrder = async (): Promise<void> => {
    setStatusActionError(null);
    try {
      await closeMutation.mutateAsync();
    } catch (error) {
      setStatusActionError(resolveWorkOrderActionError(error, t));
    }
  };

  const submitTimelineComment = async (): Promise<void> => {
    const comment = timelineCommentDraft.trim();
    if (!comment) {
      setTimelineCommentError(t("work_order_detail.error.comment_required"));
      return;
    }
    setTimelineCommentError(null);
    try {
      await addTimelineCommentMutation.mutateAsync(comment);
    } catch (error) {
      setTimelineCommentError(resolveWorkOrderActionError(error, t));
    }
  };

  const downloadDocument = async (format: "pdf" | "html" | "docx"): Promise<void> => {
    try {
      setDocumentPreviewError(null);
      setDocumentLoading(format);
      const response = await fetch(`/api/workspace/work-orders/${workOrderId}/document?format=${format}`, {
        method: "GET",
        credentials: "include"
      });
      if (!response.ok) {
        throw new Error(`${t("work_order_detail.document_error")} (${response.status})`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const contentDisposition = response.headers.get("content-disposition") ?? "";
      const fallback = `work-order-${workOrderId}.${format}`;
      const match = contentDisposition.match(/filename=\"?([^\";]+)\"?/i);
      const filename = match?.[1] ?? fallback;
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      setDocumentPreviewError(error instanceof Error ? error.message : t("work_order_detail.document_error"));
    } finally {
      setDocumentLoading(null);
    }
  };

  const loadDocumentPreview = async (): Promise<void> => {
    try {
      setDocumentPreviewError(null);
      setDocumentPreviewLoading(true);
      const response = await fetch(`/api/workspace/work-orders/${workOrderId}/document?format=html`, {
        method: "GET",
        credentials: "include"
      });
      if (!response.ok) {
        throw new Error(`${t("work_order_detail.document_preview_error")} (${response.status})`);
      }
      const html = await response.text();
      setDocumentPreviewHtml(html);
    } catch (error) {
      setDocumentPreviewHtml("");
      setDocumentPreviewError(error instanceof Error ? error.message : t("work_order_detail.document_preview_error"));
    } finally {
      setDocumentPreviewLoading(false);
    }
  };

  useEffect(() => {
    if (!documentPreviewOpen) {
      return;
    }
    void loadDocumentPreview();
  }, [documentPreviewOpen]);

  return (
    <PageLayout title={t("work_order_detail.title")}>
      <StateBoundary loading={workOrderQuery.isLoading} error={workOrderQuery.error?.message}>
        {workOrderQuery.data ? (
          <>
            <Section
              className="space-y-2"
              title={workOrderQuery.data.description}
              description={`${t("work_orders.created")} ${new Date(workOrderQuery.data.created_at).toLocaleString()}`}
              actions={
                <div className="flex items-center gap-1.5">
                  <Link href={ROUTES.workOrders}>
                    <Button variant="secondary" size="sm">
                      {t("common.back")}
                    </Button>
                  </Link>
                  <Button variant="secondary" size="sm" onClick={() => void downloadDocument("pdf")} loading={documentLoading === "pdf"}>
                    PDF
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setDocumentPreviewOpen(true)}>
                    {t("common.actions")}
                  </Button>
                </div>
              }
            >
              <div className="flex flex-wrap items-center gap-1.5">
                <Badge tone={statusTone(workOrderQuery.data.status)}>{statusLabel(workOrderQuery.data.status, t)}</Badge>
              </div>
              <p className="text-xs text-neutral-500">ID: #{workOrderQuery.data.id.slice(0, 8)}</p>

              <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-4">
                <DetailMetric label={t("work_orders.kpi.total")} value={formatMoney(workOrderQuery.data.total_amount)} accent />
                <DetailMetric label={t("work_orders.kpi.paid")} value={formatMoney(workOrderQuery.data.paid_amount)} />
                <DetailMetric label={t("work_orders.kpi.remaining")} value={formatMoney(workOrderQuery.data.remaining_amount)} />
                <Card className="border-neutral-200 bg-neutral-0 p-2">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-neutral-600">{t("work_order_detail.payment_state")}</p>
                  <div className="mt-1.5">
                    <Badge tone={paymentStateTone(workOrderQuery.data.payment_state)}>{paymentStateLabel(workOrderQuery.data.payment_state, t)}</Badge>
                  </div>
                </Card>
              </div>

              <p className="text-xs font-semibold uppercase tracking-wide text-neutral-600">{t("work_order_detail.main_info_title")}</p>

              <div className="grid grid-cols-1 gap-2 xl:grid-cols-2">
                <Card className="space-y-2 border-neutral-200 p-2">
                  <div className="space-y-1 rounded-md border border-neutral-100 bg-neutral-50/60 p-2">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-neutral-600">{t("common.client")}</p>
                    <p className="text-sm font-semibold text-neutral-900">{workOrderQuery.data.client_name ?? t("common.not_set")}</p>
                  </div>

                  <div className="space-y-1 rounded-md border border-neutral-100 bg-neutral-50/60 p-2">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-neutral-600">{t("common.vehicle")}</p>
                    <p className="text-sm font-medium text-neutral-900">
                      {attachedVehicleQuery.data
                        ? `${attachedVehicleQuery.data.plate_number} - ${attachedVehicleQuery.data.make_model}`
                        : workOrderQuery.data.vehicle_make_model ?? t("common.not_set")}
                    </p>
                  </div>

                  <div className="space-y-1 rounded-md border border-neutral-100 bg-neutral-50/60 p-2">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-neutral-600">{t("work_order_detail.current_assignee")}</p>
                    <p className="text-sm font-medium text-neutral-900">{currentAssigneeLabel}</p>
                    <div className="pt-1">
                      <Combobox
                        id="assign-employee"
                        value={workOrderQuery.data.assigned_employee_id ?? "__unassigned"}
                        onChange={(value) => {
                          assignMutation.mutate(value === "__unassigned" ? null : value);
                        }}
                        options={employeeOptions}
                        placeholder={t("work_order_detail.assign_employee")}
                        searchPlaceholder={t("work_order_detail.find_employee")}
                        emptyText={t("datatable.empty.title")}
                      />
                    </div>
                    {employeesQuery.error ? <p className="text-xs text-error">{t("work_order_detail.error.employees_load")}</p> : null}
                    {!employeesQuery.isLoading && !employeesQuery.error && (employeesQuery.data?.items.length ?? 0) === 0 ? (
                      <p className="text-xs text-neutral-600">{t("work_order_detail.no_employees_available")}</p>
                    ) : null}
                  </div>
                </Card>

                <Card className="space-y-2 border-neutral-200 p-2">
                  <div className="space-y-1 rounded-md border border-neutral-100 bg-neutral-50/60 p-2">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-neutral-600">{t("common.status")}</p>
                    <div className="flex items-center gap-1.5">
                      <Badge tone={statusTone(workOrderQuery.data.status)}>{statusLabel(workOrderQuery.data.status, t)}</Badge>
                      <span className="text-xs text-neutral-600">{paymentStateLabel(workOrderQuery.data.payment_state, t)}</span>
                    </div>
                  </div>

                  <div className="space-y-1 rounded-md border border-neutral-100 bg-neutral-50/60 p-2">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-neutral-600">{t("work_order_detail.status_controls")}</p>
                    <div className="flex flex-wrap gap-1">
                      {availableStatusTransitions.includes("in_progress") ? (
                        <Button variant="secondary" size="sm" onClick={() => void runStatusTransition("in_progress")} disabled={statusMutation.isPending}>
                          {t("work_order_detail.set_in_progress")}
                        </Button>
                      ) : null}
                      {availableStatusTransitions.includes("completed_unpaid") ? (
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => void runStatusTransition("completed_unpaid")}
                          disabled={statusMutation.isPending || !canSetCompletedUnpaid}
                        >
                          {t("work_order_detail.set_completed_unpaid")}
                        </Button>
                      ) : null}
                      {availableStatusTransitions.includes("completed_paid") ? (
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => void runStatusTransition("completed_paid")}
                          disabled={statusMutation.isPending || !canSetCompletedPaid}
                        >
                          {t("work_order_detail.set_completed_paid")}
                        </Button>
                      ) : null}
                      {availableStatusTransitions.includes("cancelled") ? (
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => void runStatusTransition("cancelled")}
                          disabled={statusMutation.isPending || !canCancelOrder}
                        >
                          {t("common.cancel")}
                        </Button>
                      ) : null}
                      {workOrderQuery.data.status !== "cancelled" ? (
                        <Button size="sm" onClick={() => void runCloseOrder()} loading={closeMutation.isPending}>
                          {t("work_order_detail.close_order")}
                        </Button>
                      ) : null}
                    </div>
                    {!canSetCompletedPaid && availableStatusTransitions.includes("completed_paid") ? (
                      <p className="text-xs text-neutral-600">{t("work_order_detail.error.cannot_mark_completed_paid")}</p>
                    ) : null}
                    {!canCancelOrder && availableStatusTransitions.includes("cancelled") ? (
                      <p className="text-xs text-neutral-600">{t("work_order_detail.error.cannot_cancel_paid_order")}</p>
                    ) : null}
                    {statusActionError ? <p className="text-xs text-error">{statusActionError}</p> : null}
                    {availableStatusTransitions.length === 0 && workOrderQuery.data.status === "cancelled" ? (
                      <p className="text-xs text-neutral-600">{t("work_order_detail.status_final")}</p>
                    ) : null}
                  </div>

                  <div className="space-y-1 rounded-md border border-neutral-100 bg-neutral-50/60 p-2">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-neutral-600">{t("work_order_detail.payments.title")}</p>
                    <div className="flex items-center justify-between gap-2">
                      <div className="space-y-0.5">
                        <p className="text-xs text-neutral-600">
                          {t("work_orders.kpi.paid")}: <span className="font-semibold text-neutral-900">{formatMoney(workOrderQuery.data.paid_amount)}</span>
                        </p>
                        <p className="text-xs text-neutral-600">
                          {t("work_orders.kpi.remaining")}: <span className="font-semibold text-neutral-900">{formatMoney(workOrderQuery.data.remaining_amount)}</span>
                        </p>
                      </div>
                      <Button variant="secondary" size="sm" onClick={() => setPaymentModalOpen(true)} disabled={!canAddPayment}>
                        {t("work_order_detail.payments.add")}
                      </Button>
                    </div>
                    {!canAddPayment ? <p className="text-xs text-neutral-600">{t("work_order_detail.error.payment_not_allowed_for_cancelled")}</p> : null}
                  </div>
                </Card>
              </div>
            </Section>

            <Section
              title={t("work_order_detail.lines.title")}
              description={t("work_order_detail.lines.description")}
              actions={
                <Button
                  onClick={() => {
                    if (!areLinesEditable) {
                      return;
                    }
                    setLineModalOpen(true);
                  }}
                  variant="secondary"
                  disabled={!areLinesEditable}
                >
                  {t("work_order_detail.lines.add")}
                </Button>
              }
            >
              {!areLinesEditable ? <p className="text-xs text-neutral-600">{t("work_order_detail.error.lines_locked")}</p> : null}
              {lineActionError ? <p className="text-sm text-error">{lineActionError}</p> : null}
              {linesQuery.isLoading ? (
                <p className="text-sm text-neutral-600">{t("work_order_detail.loading_lines")}</p>
              ) : linesQuery.error ? (
                <p className="text-sm text-error">{linesQuery.error.message}</p>
              ) : linesQuery.data?.length ? (
                <div className="space-y-1">
                  {linesQuery.data.map((line) => (
                    <Card key={line.id} className="border-neutral-200 p-2">
                      <div className="flex flex-wrap items-start justify-between gap-1">
                        <div>
                          <p className="text-sm font-medium text-neutral-900">
                            {line.name} ({t(`work_order_detail.line_type.${line.line_type}`)})
                          </p>
                          <p className="text-xs text-neutral-600">
                            {t("work_order_detail.qty_formula", {
                              quantity: line.quantity,
                              unit_price: formatMoney(line.unit_price),
                              total: formatMoney(line.line_total)
                            })}
                          </p>
                        </div>
                        <div className="flex items-center gap-1">
                          <Button variant="secondary" size="sm" onClick={() => openEditLineModal(line)} disabled={!areLinesEditable}>
                            {t("common.edit")}
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            disabled={!areLinesEditable || deleteLineMutation.isPending}
                            onClick={async () => {
                              if (!areLinesEditable) {
                                return;
                              }
                              setLineActionError(null);
                              try {
                                await deleteLineMutation.mutateAsync(line.id);
                              } catch (error) {
                                setLineActionError(resolveWorkOrderActionError(error, t));
                              }
                            }}
                          >
                            {t("common.remove")}
                          </Button>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-neutral-600">{t("work_order_detail.no_lines")}</p>
              )}
            </Section>

            <Section
              title={t("work_order_detail.payments.title")}
              description={t("work_order_detail.payments.description")}
              actions={
                <Button onClick={() => setPaymentModalOpen(true)} variant="secondary" disabled={!canAddPayment}>
                  {t("work_order_detail.payments.add")}
                </Button>
              }
            >
              {!canAddPayment ? <p className="text-xs text-neutral-600">{t("work_order_detail.error.payment_not_allowed_for_cancelled")}</p> : null}
              {paymentsQuery.isLoading ? (
                <p className="text-sm text-neutral-600">{t("work_order_detail.loading_payments")}</p>
              ) : paymentsQuery.error ? (
                <p className="text-sm text-error">{paymentsQuery.error.message}</p>
              ) : paymentsQuery.data?.length ? (
                <div className="space-y-1">
                  {paymentsQuery.data.map((payment) => (
                    <Card key={payment.id} className="border-neutral-200 p-2">
                      <div className="flex flex-wrap items-start justify-between gap-1">
                        <div>
                          <p className="text-sm font-medium text-neutral-900">{formatMoney(payment.amount)}</p>
                          <p className="text-xs text-neutral-600">
                            {t(`work_order_detail.payment_method.${payment.method}`)} - {new Date(payment.paid_at).toLocaleString()}
                          </p>
                          {payment.comment ? <p className="text-xs text-neutral-600">{payment.comment}</p> : null}
                        </div>
                        <Badge tone="neutral">{t("work_order_detail.payment")}</Badge>
                      </div>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-neutral-600">{t("work_order_detail.no_payments")}</p>
              )}
            </Section>

            <Section title={t("work_order_detail.timeline.title")} description={t("work_order_detail.timeline.description")}>
              {timelineQuery.isLoading ? (
                <p className="text-sm text-neutral-600">{t("work_order_detail.loading_activity")}</p>
              ) : timelineQuery.error ? (
                <p className="text-sm text-error">{timelineQuery.error.message}</p>
              ) : timelineQuery.data?.length ? (
                <div className="relative pl-6">
                  <div className="absolute bottom-1 left-[11px] top-1 w-px bg-neutral-200" aria-hidden />
                  {timelineQuery.data.map((item, index) => {
                    const presentation = timelinePresentation(item, t);
                    const styles = timelineKindStyles(presentation.kind);
                    const actor =
                      item.actor_email?.split("@")[0] ??
                      item.actor_email ??
                      t("work_order_detail.timeline.system");
                    const role =
                      item.actor_role && ["owner", "admin", "manager", "employee"].includes(item.actor_role)
                        ? t(`employees.role.${item.actor_role}`)
                        : item.actor_role ?? null;
                    const metaParts = [actor, role, new Date(item.created_at).toLocaleString()].filter(Boolean);

                    return (
                      <div key={item.id} className={cn("relative pb-2.5", index === timelineQuery.data.length - 1 && "pb-0")}>
                        <span
                          className={cn(
                            "absolute left-0 top-1.5 h-[10px] w-[10px] rounded-full ring-4 ring-neutral-0",
                            styles.dotClass
                          )}
                          aria-hidden
                        />

                        <div className="ml-4 rounded-md border border-neutral-100 bg-neutral-50/70 px-3 py-2">
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                              <div className="flex flex-wrap items-center gap-1.5">
                                <span className={cn("inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide", styles.chipClass)}>
                                  {presentation.typeLabel}
                                </span>
                                <p className="text-sm font-semibold text-neutral-900">{presentation.title}</p>
                              </div>

                              {presentation.statusFrom && presentation.statusTo ? (
                                <div className="mt-1 flex flex-wrap items-center gap-1.5">
                                  <Badge tone={statusTone(presentation.statusFrom)}>{statusLabel(presentation.statusFrom, t)}</Badge>
                                  <span className="text-xs text-neutral-500">{"->"}</span>
                                  <Badge tone={statusTone(presentation.statusTo)}>{statusLabel(presentation.statusTo, t)}</Badge>
                                </div>
                              ) : presentation.details ? (
                                <p className="mt-1 text-xs font-medium text-neutral-700">{presentation.details}</p>
                              ) : null}

                              <p className="mt-1 text-xs text-neutral-600">{metaParts.join(" | ")}</p>
                            </div>

                            <p className="shrink-0 text-[11px] text-neutral-500">{formatRelativeTime(item.created_at, locale)}</p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-sm text-neutral-600">{t("work_order_detail.no_activity")}</p>
              )}

              <Card className="border-neutral-200 bg-neutral-50/70 p-2">
                <FormField id="timeline-comment" label={t("work_order_detail.comments.add_label")}>
                  <div className="space-y-2">
                    <Textarea
                      id="timeline-comment"
                      className="min-h-20"
                      value={timelineCommentDraft}
                      placeholder={t("work_order_detail.comments.placeholder")}
                      onChange={(event) => {
                        setTimelineCommentDraft(event.target.value);
                        if (timelineCommentError) {
                          setTimelineCommentError(null);
                        }
                      }}
                    />
                    <div className="flex items-center justify-end">
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => void submitTimelineComment()}
                        loading={addTimelineCommentMutation.isPending}
                      >
                        {t("work_order_detail.comments.add_action")}
                      </Button>
                    </div>
                    {timelineCommentError ? <p className="text-sm text-error">{timelineCommentError}</p> : null}
                  </div>
                </FormField>
              </Card>
            </Section>

          </>
        ) : null}
      </StateBoundary>

      <Modal
        open={documentPreviewOpen}
        onOpenChange={setDocumentPreviewOpen}
        title={t("work_order_detail.document_modal_title")}
        description={t("work_order_detail.document_modal_description")}
        size="lg"
        footer={
          <FormActions>
            <Button variant="secondary" onClick={() => setDocumentPreviewOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button variant="secondary" onClick={() => void loadDocumentPreview()} loading={documentPreviewLoading}>
              {t("work_order_detail.document_refresh_preview")}
            </Button>
            <Button onClick={() => void downloadDocument(documentFormat)} loading={documentLoading === documentFormat}>
              {t("work_order_detail.document_download_selected")}
            </Button>
          </FormActions>
        }
      >
        <div className="space-y-2">
          <FormField id="document-format" label={t("work_order_detail.document_format_label")}>
            <Select id="document-format" value={documentFormat} onChange={(event) => setDocumentFormat(event.target.value as "pdf" | "html" | "docx")}>
              <option value="pdf">PDF</option>
              <option value="docx">Word (DOCX)</option>
              <option value="html">HTML</option>
            </Select>
          </FormField>
          <p className="text-xs text-neutral-600">{t("work_order_detail.document_preview_note")}</p>

          <div className="rounded-md border border-neutral-200 p-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{t("work_order_detail.document_preview_title")}</p>
            <div className="mt-2 h-[420px] overflow-hidden rounded-md border border-neutral-200 bg-neutral-50">
              {documentPreviewLoading ? (
                <div className="flex h-full items-center justify-center px-3 text-sm text-neutral-600">
                  {t("work_order_detail.document_preview_loading")}
                </div>
              ) : documentPreviewError ? (
                <div className="flex h-full items-center justify-center px-3 text-sm text-error">{documentPreviewError}</div>
              ) : documentPreviewHtml ? (
                <iframe
                  title={t("work_order_detail.document_preview_title")}
                  className="h-full w-full bg-neutral-0"
                  srcDoc={documentPreviewHtml}
                />
              ) : (
                <div className="flex h-full items-center justify-center px-3 text-sm text-neutral-600">
                  {t("work_order_detail.document_preview_empty")}
                </div>
              )}
            </div>
          </div>
        </div>
      </Modal>

      <Modal
        open={lineModalOpen}
        onOpenChange={(open) => {
          if (open && !areLinesEditable) {
            setLineError(t("work_order_detail.error.lines_locked"));
            return;
          }
          setLineModalOpen(open);
          if (!open) {
            setLineError(null);
          }
        }}
        title={t("work_order_detail.lines.add")}
        description={t("work_order_detail.lines.description")}
        footer={
          <FormActions>
            <Button variant="secondary" onClick={() => setLineModalOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button
              onClick={async () => {
                const quantity = Number(lineDraft.quantity);
                const unitPrice = Number(lineDraft.unit_price);
                if (!areLinesEditable) {
                  setLineError(t("work_order_detail.error.lines_locked"));
                  return;
                }
                if (!lineDraft.name.trim() || !Number.isFinite(quantity) || !Number.isFinite(unitPrice) || unitPrice <= 0 || quantity <= 0) {
                  setLineError(t("work_order_detail.error.line_required"));
                  return;
                }
                setLineError(null);
                try {
                  await addLineMutation.mutateAsync({
                    line_type: lineDraft.line_type,
                    name: lineDraft.name.trim(),
                    quantity,
                    unit_price: unitPrice,
                    comment: lineDraft.comment.trim() || null
                  });
                  setLineModalOpen(false);
                  setLineDraft({ line_type: "labor", name: "", quantity: "1", unit_price: "", comment: "" });
                } catch (error) {
                  setLineError(resolveWorkOrderActionError(error, t));
                }
              }}
              loading={addLineMutation.isPending}
            >
              {t("work_order_detail.lines.add")}
            </Button>
          </FormActions>
        }
      >
        <div className="space-y-2">
          <FormField id="line-type" label={t("common.type")}>
            <Select
              id="line-type"
              value={lineDraft.line_type}
              onChange={(event) => setLineDraft((prev) => ({ ...prev, line_type: event.target.value as "labor" | "part" | "misc" }))}
            >
              <option value="labor">{t("work_order_detail.line_type.labor")}</option>
              <option value="part">{t("work_order_detail.line_type.part")}</option>
              <option value="misc">{t("work_order_detail.line_type.misc")}</option>
            </Select>
          </FormField>
          <FormField id="line-name" label={t("common.name")} required>
            <Input id="line-name" value={lineDraft.name} onChange={(event) => setLineDraft((prev) => ({ ...prev, name: event.target.value }))} />
          </FormField>
          <FormField id="line-qty" label={t("common.quantity")} required>
            <Input id="line-qty" value={lineDraft.quantity} onChange={(event) => setLineDraft((prev) => ({ ...prev, quantity: event.target.value }))} />
          </FormField>
          <FormField id="line-unit-price" label={t("common.unit_price")} required>
            <Input
              id="line-unit-price"
              value={lineDraft.unit_price}
              onChange={(event) => setLineDraft((prev) => ({ ...prev, unit_price: event.target.value }))}
            />
          </FormField>
          <FormField id="line-comment" label={t("common.comment")}>
            <Textarea
              id="line-comment"
              value={lineDraft.comment}
              onChange={(event) => setLineDraft((prev) => ({ ...prev, comment: event.target.value }))}
            />
          </FormField>
          {lineError ? <p className="text-sm text-error">{lineError}</p> : null}
        </div>
      </Modal>

      <Modal
        open={editLineModalOpen}
        onOpenChange={(open) => {
          if (open && !areLinesEditable) {
            setEditLineError(t("work_order_detail.error.lines_locked"));
            return;
          }
          setEditLineModalOpen(open);
          if (!open) {
            setEditingLine(null);
            setEditLineError(null);
          }
        }}
        title={t("work_order_detail.lines.edit")}
        description={editingLine ? `${t("common.line")} ${editingLine.name}` : t("work_order_detail.lines.edit_description")}
        footer={
          <FormActions>
            <Button variant="secondary" onClick={() => setEditLineModalOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button
              onClick={async () => {
                if (!editingLine) {
                  return;
                }
                if (!areLinesEditable) {
                  setEditLineError(t("work_order_detail.error.lines_locked"));
                  return;
                }
                const quantity = Number(editLineDraft.quantity);
                const unitPrice = Number(editLineDraft.unit_price);
                if (!editLineDraft.name.trim() || !Number.isFinite(quantity) || !Number.isFinite(unitPrice) || unitPrice <= 0 || quantity <= 0) {
                  setEditLineError(t("work_order_detail.error.line_required"));
                  return;
                }
                setEditLineError(null);
                try {
                  await updateLineMutation.mutateAsync({
                    lineId: editingLine.id,
                    payload: {
                      line_type: editLineDraft.line_type,
                      name: editLineDraft.name.trim(),
                      quantity,
                      unit_price: unitPrice,
                      comment: editLineDraft.comment.trim() || null
                    }
                  });
                  setEditLineModalOpen(false);
                  setEditingLine(null);
                } catch (error) {
                  setEditLineError(resolveWorkOrderActionError(error, t));
                }
              }}
              loading={updateLineMutation.isPending}
            >
              {t("common.save")}
            </Button>
          </FormActions>
        }
      >
        <div className="space-y-2">
          <FormField id="edit-line-type" label={t("common.type")}>
            <Select
              id="edit-line-type"
              value={editLineDraft.line_type}
              onChange={(event) => setEditLineDraft((prev) => ({ ...prev, line_type: event.target.value as "labor" | "part" | "misc" }))}
            >
              <option value="labor">{t("work_order_detail.line_type.labor")}</option>
              <option value="part">{t("work_order_detail.line_type.part")}</option>
              <option value="misc">{t("work_order_detail.line_type.misc")}</option>
            </Select>
          </FormField>
          <FormField id="edit-line-name" label={t("common.name")} required>
            <Input
              id="edit-line-name"
              value={editLineDraft.name}
              onChange={(event) => setEditLineDraft((prev) => ({ ...prev, name: event.target.value }))}
            />
          </FormField>
          <FormField id="edit-line-qty" label={t("common.quantity")} required>
            <Input
              id="edit-line-qty"
              value={editLineDraft.quantity}
              onChange={(event) => setEditLineDraft((prev) => ({ ...prev, quantity: event.target.value }))}
            />
          </FormField>
          <FormField id="edit-line-unit-price" label={t("common.unit_price")} required>
            <Input
              id="edit-line-unit-price"
              value={editLineDraft.unit_price}
              onChange={(event) => setEditLineDraft((prev) => ({ ...prev, unit_price: event.target.value }))}
            />
          </FormField>
          <FormField id="edit-line-comment" label={t("common.comment")}>
            <Textarea
              id="edit-line-comment"
              value={editLineDraft.comment}
              onChange={(event) => setEditLineDraft((prev) => ({ ...prev, comment: event.target.value }))}
            />
          </FormField>
          {editLineError ? <p className="text-sm text-error">{editLineError}</p> : null}
        </div>
      </Modal>

      <Modal
        open={paymentModalOpen}
        onOpenChange={(open) => {
          if (open && !canAddPayment) {
            setPaymentError(t("work_order_detail.error.payment_not_allowed_for_cancelled"));
            return;
          }
          setPaymentModalOpen(open);
          if (!open) {
            setPaymentError(null);
          }
        }}
        title={t("work_order_detail.payments.add")}
        description={t("work_order_detail.payments.description")}
        footer={
          <FormActions>
            <Button variant="secondary" onClick={() => setPaymentModalOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button
              onClick={async () => {
                const amount = Number(paymentDraft.amount);
                if (!canAddPayment) {
                  setPaymentError(t("work_order_detail.error.payment_not_allowed_for_cancelled"));
                  return;
                }
                if (!Number.isFinite(amount) || amount <= 0) {
                  setPaymentError(t("work_order_detail.error.payment_amount"));
                  return;
                }
                setPaymentError(null);
                try {
                  await addPaymentMutation.mutateAsync({
                    amount,
                    method: paymentDraft.method,
                    comment: paymentDraft.comment.trim() || null
                  });
                  setPaymentModalOpen(false);
                  setPaymentDraft({ amount: "", method: "cash", comment: "" });
                } catch (error) {
                  setPaymentError(resolveWorkOrderActionError(error, t));
                }
              }}
              loading={addPaymentMutation.isPending}
            >
              {t("work_order_detail.payments.add")}
            </Button>
          </FormActions>
        }
      >
        <div className="space-y-2">
          <FormField id="payment-amount" label={t("common.amount")} required>
            <Input
              id="payment-amount"
              value={paymentDraft.amount}
              onChange={(event) => setPaymentDraft((prev) => ({ ...prev, amount: event.target.value }))}
            />
          </FormField>
          <FormField id="payment-method" label={t("common.method")} required>
            <Select
              id="payment-method"
              value={paymentDraft.method}
              onChange={(event) =>
                setPaymentDraft((prev) => ({ ...prev, method: event.target.value as "cash" | "card" | "transfer" | "other" }))
              }
            >
              <option value="cash">{t("work_order_detail.payment_method.cash")}</option>
              <option value="card">{t("work_order_detail.payment_method.card")}</option>
              <option value="transfer">{t("work_order_detail.payment_method.transfer")}</option>
              <option value="other">{t("work_order_detail.payment_method.other")}</option>
            </Select>
          </FormField>
          <FormField id="payment-comment" label={t("common.comment")}>
            <Textarea
              id="payment-comment"
              value={paymentDraft.comment}
              onChange={(event) => setPaymentDraft((prev) => ({ ...prev, comment: event.target.value }))}
            />
          </FormField>
          {paymentError ? <p className="text-sm text-error">{paymentError}</p> : null}
        </div>
      </Modal>
    </PageLayout>
  );
}


