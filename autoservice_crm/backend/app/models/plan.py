from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Plan(BaseModel):
    """Commercial plan definition used by subscriptions."""

    __tablename__ = "plans"

    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    limits_json: Mapped[dict[str, Any]] = mapped_column(
        "limits",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    features_json: Mapped[dict[str, Any]] = mapped_column(
        "features",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
