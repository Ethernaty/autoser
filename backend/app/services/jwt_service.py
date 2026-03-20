from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
from pydantic import BaseModel, ValidationError

from app.core.cache import get_cache_backend
from app.core.cache.cache_backend import SyncCacheAdapter, get_sync_cache_adapter
from app.core.config import get_settings
from app.core.exceptions import AuthError


class TokenType:
    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(BaseModel):
    sub: str
    tenant_id: str
    role: str
    mv: int
    token_type: str
    iat: int
    exp: int
    jti: str

    @property
    def user_id(self) -> UUID:
        return UUID(self.sub)

    @property
    def tenant_uuid(self) -> UUID:
        return UUID(self.tenant_id)

    @property
    def membership_version(self) -> int:
        return int(self.mv)


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str
    access_expires_in: int
    refresh_expires_in: int


class JWTService:
    """JWT issue/validate/revoke service."""

    def __init__(
        self,
        *,
        secret_key: str,
        algorithm: str,
        access_ttl_minutes: int,
        refresh_ttl_days: int,
        sync_cache: SyncCacheAdapter,
    ):
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_ttl_minutes = access_ttl_minutes
        self._refresh_ttl_days = refresh_ttl_days
        self._sync_cache = sync_cache

    def issue_token_pair(self, *, user_id: UUID, tenant_id: UUID, role: str, membership_version: int) -> TokenPair:
        access_ttl = timedelta(minutes=self._access_ttl_minutes)
        refresh_ttl = timedelta(days=self._refresh_ttl_days)

        access_token = self._encode(
            user_id=user_id,
            tenant_id=tenant_id,
            role=role,
            membership_version=membership_version,
            token_type=TokenType.ACCESS,
            ttl=access_ttl,
        )
        refresh_token = self._encode(
            user_id=user_id,
            tenant_id=tenant_id,
            role=role,
            membership_version=membership_version,
            token_type=TokenType.REFRESH,
            ttl=refresh_ttl,
        )
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            access_expires_in=int(access_ttl.total_seconds()),
            refresh_expires_in=int(refresh_ttl.total_seconds()),
        )

    def decode(self, token: str, *, expected_type: str, check_revoked: bool = True) -> TokenPayload:
        payload = self._decode_and_validate(token=token, expected_type=expected_type)

        if check_revoked and self.is_revoked(payload.jti):
            raise AuthError(code="token_revoked", message="Token has been revoked")

        return payload

    async def decode_async(
        self,
        token: str,
        *,
        expected_type: str,
        check_revoked: bool = True,
        fail_closed: bool = True,
    ) -> TokenPayload:
        payload = self._decode_and_validate(token=token, expected_type=expected_type)

        if check_revoked:
            try:
                revoked = await self.is_revoked_async(payload.jti)
            except Exception as exc:
                if fail_closed:
                    raise AuthError(code="auth_backend_unavailable", message="Auth backend unavailable") from exc
                revoked = False
            if revoked:
                raise AuthError(code="token_revoked", message="Token has been revoked")

        return payload

    def revoke(self, payload: TokenPayload) -> None:
        ttl = max(1, payload.exp - int(datetime.now(UTC).timestamp()))
        self._sync_cache.set(self._revocation_key(payload.jti), 1, ttl)

    def revoke_token(self, token: str, *, expected_type: str) -> TokenPayload:
        payload = self.decode(token, expected_type=expected_type, check_revoked=False)
        self.revoke(payload)
        return payload

    def is_revoked(self, jti: str) -> bool:
        return self._sync_cache.get(self._revocation_key(jti)) is not None

    async def is_revoked_async(self, jti: str) -> bool:
        backend = get_cache_backend()
        value = await backend.get(self._revocation_key(jti))
        return value is not None

    def _decode_and_validate(self, *, token: str, expected_type: str) -> TokenPayload:
        try:
            decoded = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
        except jwt.ExpiredSignatureError as exc:
            raise AuthError(code="token_expired", message="Token expired") from exc
        except jwt.InvalidTokenError as exc:
            raise AuthError(code="invalid_token", message="Invalid token") from exc

        try:
            payload = TokenPayload.model_validate(decoded)
        except ValidationError as exc:
            raise AuthError(code="invalid_token_payload", message="Invalid token payload") from exc

        if payload.token_type != expected_type:
            raise AuthError(code="invalid_token_type", message="Invalid token type")

        return payload

    def _encode(
        self,
        *,
        user_id: UUID,
        tenant_id: UUID,
        role: str,
        membership_version: int,
        token_type: str,
        ttl: timedelta,
    ) -> str:
        now = datetime.now(UTC)
        exp = now + ttl
        payload: dict[str, Any] = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "role": role,
            "mv": int(membership_version),
            "token_type": token_type,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "jti": str(uuid4()),
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    @staticmethod
    def _revocation_key(jti: str) -> str:
        return f"auth:revoked:{jti}"


def extract_bearer_token(authorization_header: str | None) -> str:
    if not authorization_header:
        raise AuthError(code="missing_token", message="Authorization token is required")
    parts = authorization_header.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthError(code="invalid_auth_scheme", message="Use Authorization: Bearer <token>")
    return parts[1]


def get_jwt_service() -> JWTService:
    settings = get_settings()
    return JWTService(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        access_ttl_minutes=settings.access_token_expires_minutes,
        refresh_ttl_days=settings.refresh_token_expires_days,
        sync_cache=get_sync_cache_adapter(),
    )
