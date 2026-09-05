from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.controllers.schemas.support_schemas import (
    SupportTicketCreateRequest,
    SupportTicketListResponse,
    SupportTicketMessageCreateRequest,
    SupportTicketResponse,
    SupportTicketUpdateStatusRequest,
)
from app.core.config import get_settings
from app.core.request_context import UserRequestContext, get_current_tenant_id, get_current_user_context
from app.middleware.permission_guard import RequirePermission
from app.models.support_ticket import SupportTicketCategory, SupportTicketStatus
from app.services.support_ticket_service import SupportTicketService


router = APIRouter(prefix="/support/tickets", tags=["Support"])
MAX_LIMIT = get_settings().max_limit


def get_support_ticket_service(
    tenant_id: UUID = Depends(get_current_tenant_id),
    context: UserRequestContext = Depends(get_current_user_context),
) -> SupportTicketService:
    return SupportTicketService(
        tenant_id=tenant_id,
        actor_user_id=context.user_id,
        actor_role=context.role,
    )


@router.get("/", response_model=SupportTicketListResponse, dependencies=[Depends(RequirePermission("support", "read"))])
async def list_support_tickets(
    query: str | None = Query(default=None, alias="q"),
    status: SupportTicketStatus | None = Query(default=None),
    category: SupportTicketCategory | None = Query(default=None),
    my_only: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    service: SupportTicketService = Depends(get_support_ticket_service),
) -> SupportTicketListResponse:
    items, total = await service.list_tickets(
        limit=limit,
        offset=offset,
        q=query,
        status=status,
        category=category,
        my_only=my_only,
    )
    return SupportTicketListResponse(
        items=[SupportTicketResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/", response_model=SupportTicketResponse, dependencies=[Depends(RequirePermission("support", "create"))])
async def create_support_ticket(
    payload: SupportTicketCreateRequest,
    service: SupportTicketService = Depends(get_support_ticket_service),
) -> SupportTicketResponse:
    ticket = await service.create_ticket(
        subject=payload.subject,
        category=payload.category,
        message=payload.message,
    )
    return SupportTicketResponse.model_validate(ticket)


@router.patch(
    "/{ticket_id}/status",
    response_model=SupportTicketResponse,
    dependencies=[Depends(RequirePermission("support", "update"))],
)
async def update_support_ticket_status(
    ticket_id: UUID,
    payload: SupportTicketUpdateStatusRequest,
    service: SupportTicketService = Depends(get_support_ticket_service),
) -> SupportTicketResponse:
    ticket = await service.update_status(ticket_id=ticket_id, status=payload.status)
    return SupportTicketResponse.model_validate(ticket)


@router.post(
    "/{ticket_id}/messages",
    response_model=SupportTicketResponse,
    dependencies=[Depends(RequirePermission("support", "create"))],
)
async def add_support_ticket_message(
    ticket_id: UUID,
    payload: SupportTicketMessageCreateRequest,
    service: SupportTicketService = Depends(get_support_ticket_service),
) -> SupportTicketResponse:
    ticket = await service.add_message(ticket_id=ticket_id, message=payload.message)
    return SupportTicketResponse.model_validate(ticket)
