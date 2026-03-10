from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.core.exceptions import AppError


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


class TokenType:
    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(BaseModel):
    sub: str
    tenant_id: str
    role: str
    token_type: str
    exp: int
    iat: int
    jti: str

    @property
    def user_id(self) -> UUID:
        return UUID(self.sub)

    @property
    def tenant_uuid(self) -> UUID:
        return UUID(self.tenant_id)


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_expires_in: int = 0
    refresh_expires_in: int = 0


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_token(
    *,
    user_id: UUID,
    tenant_id: UUID,
    role: str,
    token_type: str,
    expires_delta: timedelta,
) -> str:
    issued_at = datetime.now(UTC)
    expire_at = issued_at + expires_delta
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "token_type": token_type,
        "iat": int(issued_at.timestamp()),
        "exp": int(expire_at.timestamp()),
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_token_pair(*, user_id: UUID, tenant_id: UUID, role: str) -> TokenPair:
    access_delta = timedelta(minutes=settings.access_token_expires_minutes)
    refresh_delta = timedelta(days=settings.refresh_token_expires_days)

    access_token = create_token(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        token_type=TokenType.ACCESS,
        expires_delta=access_delta,
    )
    refresh_token = create_token(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        token_type=TokenType.REFRESH,
        expires_delta=refresh_delta,
    )
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_in=int(access_delta.total_seconds()),
        refresh_expires_in=int(refresh_delta.total_seconds()),
    )


def decode_token(token: str, expected_type: str) -> TokenPayload:
    try:
        decoded = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise AppError(status_code=401, code="token_expired", message="Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AppError(status_code=401, code="invalid_token", message="Invalid token") from exc

    try:
        payload = TokenPayload.model_validate(decoded)
    except ValidationError as exc:
        raise AppError(status_code=401, code="invalid_token_payload", message="Invalid token payload") from exc
    if payload.token_type != expected_type:
        raise AppError(status_code=401, code="invalid_token_type", message="Invalid token type")
    return payload
