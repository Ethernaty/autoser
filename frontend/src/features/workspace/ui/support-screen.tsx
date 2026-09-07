"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Button, Card, FormField, Input, Select, Textarea } from "@/design-system/primitives";
import { PageLayout, Section, StateBoundary } from "@/design-system/patterns";
import { hasPermission } from "@/features/rbac/config/permission-matrix";
import { addSupportTicketMessage, createSupportTicket, fetchSupportTickets, mvpQueryKeys, updateSupportTicketStatus } from "@/features/workspace/api/mvp-api";
import type { SupportTicketCategory, SupportTicketStatus } from "@/features/workspace/types/mvp-types";
import { useAuthStore } from "@/features/auth/model/auth-store";
import { useI18n } from "@/shared/i18n";

const CATEGORY_OPTIONS: SupportTicketCategory[] = ["general", "bug", "payment", "data", "access", "other"];
const STATUS_OPTIONS: Array<SupportTicketStatus | "all"> = ["all", "open", "in_progress", "resolved", "closed"];

function statusTone(status: SupportTicketStatus): "neutral" | "warning" | "success" {
  if (status === "resolved" || status === "closed") {
    return "success";
  }
  if (status === "in_progress") {
    return "warning";
  }
  return "neutral";
}

export function SupportScreen(): JSX.Element {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const session = useAuthStore((state) => state.session);
  const canUpdateStatus = hasPermission(session?.role ?? "employee", "support.update");

  const [subject, setSubject] = useState("");
  const [category, setCategory] = useState<SupportTicketCategory>("general");
  const [message, setMessage] = useState("");
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<SupportTicketStatus | "all">("all");
  const [categoryFilter, setCategoryFilter] = useState<SupportTicketCategory | "all">("all");
  const [myOnly, setMyOnly] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [createdTicketId, setCreatedTicketId] = useState<string | null>(null);
  const [replyDrafts, setReplyDrafts] = useState<Record<string, string>>({});

  const ticketsQuery = useQuery({
    queryKey: mvpQueryKeys.supportTickets(q, status, categoryFilter, myOnly, 50, 0),
    queryFn: () =>
      fetchSupportTickets({
        q: q || undefined,
        status: status === "all" ? undefined : status,
        category: categoryFilter === "all" ? undefined : categoryFilter,
        my_only: myOnly,
        limit: 50,
        offset: 0
      })
  });

  const createTicketMutation = useMutation({
    mutationFn: createSupportTicket,
    onSuccess: (ticket) => {
      setSubject("");
      setCategory("general");
      setMessage("");
      setFormError(null);
      setCreatedTicketId(ticket.id);
      void queryClient.invalidateQueries({ queryKey: ["support", "tickets"] });
    }
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ ticketId, status }: { ticketId: string; status: SupportTicketStatus }) =>
      updateSupportTicketStatus(ticketId, status),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["support", "tickets"] });
    }
  });

  const replyMutation = useMutation({
    mutationFn: ({ ticketId, message }: { ticketId: string; message: string }) => addSupportTicketMessage(ticketId, message),
    onSuccess: (_, variables) => {
      setReplyDrafts((current) => ({ ...current, [variables.ticketId]: "" }));
      void queryClient.invalidateQueries({ queryKey: ["support", "tickets"] });
    }
  });

  const ticketRows = ticketsQuery.data?.items ?? [];

  const nextStatusByCurrent = useMemo<Record<SupportTicketStatus, SupportTicketStatus | null>>(
    () => ({
      open: "in_progress",
      in_progress: "resolved",
      resolved: "closed",
      closed: null
    }),
    []
  );

  return (
    <PageLayout title={t("support.title")} subtitle={t("support.subtitle")}>
      <Section title={t("support.new_ticket")}>
        <div className="grid grid-cols-1 gap-2 lg:grid-cols-2">
          <FormField id="support-subject" label={t("support.subject")} required>
            <Input id="support-subject" value={subject} onChange={(event) => setSubject(event.target.value)} />
          </FormField>
          <FormField id="support-category" label={t("support.category")} required>
            <Select id="support-category" value={category} onChange={(event) => setCategory(event.target.value as SupportTicketCategory)}>
              {CATEGORY_OPTIONS.map((item) => (
                <option key={item} value={item}>
                  {t(`support.category.${item}`)}
                </option>
              ))}
            </Select>
          </FormField>
        </div>
        <div className="mt-2">
          <FormField id="support-message" label={t("support.message")} required>
            <Textarea id="support-message" rows={4} value={message} onChange={(event) => setMessage(event.target.value)} />
          </FormField>
        </div>
        {formError ? <p className="mt-2 text-sm text-error">{formError}</p> : null}
        {createdTicketId ? <p className="mt-2 rounded-md bg-success/10 px-3 py-2 text-sm text-success">{t("support.created", { id: createdTicketId.slice(0, 8).toUpperCase() })}</p> : null}
        <div className="mt-2">
          <Button
            variant="primary"
            loading={createTicketMutation.isPending}
            onClick={async () => {
              if (!subject.trim() || !message.trim()) {
                setFormError(t("support.validation_required"));
                return;
              }
              await createTicketMutation.mutateAsync({
                subject: subject.trim(),
                category,
                message: message.trim()
              });
            }}
          >
            {t("support.submit")}
          </Button>
        </div>
      </Section>

      <Section title={t("support.list.title")} description={t("support.list.description")}>
        <div className="mb-2 grid grid-cols-1 gap-2 xl:grid-cols-[minmax(0,1fr)_200px_200px_auto_auto]">
          <Input placeholder={t("common.search")} value={q} onChange={(event) => setQ(event.target.value)} />
          <Select value={status} onChange={(event) => setStatus(event.target.value as SupportTicketStatus | "all")}>
            {STATUS_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option === "all" ? t("support.filter.all") : t(`support.status.${option}`)}
              </option>
            ))}
          </Select>
          <Select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value as SupportTicketCategory | "all")}>
            <option value="all">{t("support.filter.all")}</option>
            {CATEGORY_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {t(`support.category.${option}`)}
              </option>
            ))}
          </Select>
          <label className="inline-flex items-center gap-2 text-sm text-neutral-700">
            <input type="checkbox" checked={myOnly} onChange={(event) => setMyOnly(event.target.checked)} />
            {t("support.filter.my_only")}
          </label>
          <Button variant="ghost" onClick={() => {
            setQ("");
            setStatus("all");
            setCategoryFilter("all");
            setMyOnly(false);
          }}>
            {t("common.reset")}
          </Button>
        </div>

        <StateBoundary loading={ticketsQuery.isLoading} error={ticketsQuery.error?.message}>
          {ticketRows.length ? (
            <div className="space-y-1.5">
              {ticketRows.map((ticket) => {
                const nextStatus = nextStatusByCurrent[ticket.status];
                return (
                  <Card key={ticket.id} className="border-neutral-200 p-3">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-neutral-500">#{ticket.id.slice(0, 8).toUpperCase()}</p>
                        <p className="truncate text-sm font-semibold text-neutral-900">{ticket.subject}</p>
                        <p className="mt-1 text-xs text-neutral-600">{ticket.message}</p>
                        <p className="mt-1 text-xs text-neutral-500">
                          {t(`support.category.${ticket.category}`)} • {new Date(ticket.created_at).toLocaleString()}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={
                            "rounded-sm px-2 py-1 text-xs font-medium " +
                            (statusTone(ticket.status) === "success"
                              ? "bg-success/10 text-success"
                              : statusTone(ticket.status) === "warning"
                                ? "bg-warning/10 text-warning"
                                : "bg-neutral-100 text-neutral-700")
                          }
                        >
                          {t(`support.status.${ticket.status}`)}
                        </span>
                        {canUpdateStatus && nextStatus ? (
                          <Button
                            size="sm"
                            variant="secondary"
                            loading={updateStatusMutation.isPending}
                            onClick={() => updateStatusMutation.mutate({ ticketId: ticket.id, status: nextStatus })}
                          >
                            {t(`support.status.${nextStatus}`)}
                          </Button>
                        ) : null}
                      </div>
                    </div>
                    {ticket.messages?.length ? (
                      <div className="mt-3 space-y-2 border-t border-neutral-200 pt-3">
                        {ticket.messages.map((item) => (
                          <div key={item.id} className="rounded-md bg-neutral-50 px-3 py-2">
                            <div className="flex items-center justify-between gap-2 text-[11px] text-neutral-500">
                              <span>{item.author_role}</span>
                              <span>{new Date(item.created_at).toLocaleString()}</span>
                            </div>
                            <p className="mt-1 whitespace-pre-wrap text-sm text-neutral-700">{item.message}</p>
                          </div>
                        ))}
                      </div>
                    ) : null}
                    <div className="mt-3 flex items-end gap-2 border-t border-neutral-200 pt-3">
                      <FormField id={`support-reply-${ticket.id}`} label={t("support.reply")} className="flex-1">
                        <Textarea
                          id={`support-reply-${ticket.id}`}
                          rows={2}
                          value={replyDrafts[ticket.id] ?? ""}
                          onChange={(event) => setReplyDrafts((current) => ({ ...current, [ticket.id]: event.target.value }))}
                        />
                      </FormField>
                      <Button
                        size="sm"
                        loading={replyMutation.isPending && replyMutation.variables?.ticketId === ticket.id}
                        disabled={!replyDrafts[ticket.id]?.trim()}
                        onClick={() => replyMutation.mutate({ ticketId: ticket.id, message: replyDrafts[ticket.id].trim() })}
                      >
                        {t("support.reply_send")}
                      </Button>
                    </div>
                  </Card>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-neutral-600">{t("support.empty")}</p>
          )}
        </StateBoundary>
      </Section>
    </PageLayout>
  );
}
