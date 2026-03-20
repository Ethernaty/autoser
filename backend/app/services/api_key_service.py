from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker
from starlette.concurrency import run_in_threadpool

from app.core.cache import CacheBackend, get_cache_backend
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.exceptions import AppError
from app.core.input_security import sanitize_text
from app.core.request_context import ApiKeyRequestContext
from app.core.serialization import JsonSerializer, Serializer
from app.models.api_key import ApiKey
from app.repositories.api_key_repository import ApiKeyRepository
from app.services.base_service import BaseService


_RAW_KEY_PREFIX = "sk_"
_LOOKUP_PREFIX_LEN = 18


@dataclass(frozen=True)
class ApiKeyIssueResult:
    api_key: ApiKey
    plain_key: str


@dataclass(frozen=True)
class ApiKeyAuthResult:
    api_key_id: UUID
    tenant_id: UUID
    scopes: list[str]
    name: str


class ApiKeyService(BaseService):
    """Tenant-scoped API key management + global API key authentication."""

    def __init__(
        self,
        *,
        tenant_id: UUID | None,
        actor_user_id: UUID | None = None,
        actor_role: str | None = None,
        session_factory: sessionmaker[Session] | None = None,
        serializer: Serializer | None = None,
        cache_backend: CacheBackend | None = None,
    ) -> None:
        self.actor_role = (actor_role or "").lower() if actor_role else None
        self._settings = get_settings()
        self._cache_ttl = max(15, self._settings.billing_cache_ttl_seconds)
        self._pepper = self._settings.api_key_secret_pepper

        if tenant_id is None:
            # Global auth mode for middleware key validation.
            self.tenant_id = UUID(int=0)
            self.actor_user_id = actor_user_id
            self._session_factory = session_factory or SessionLocal
            self.serializer = serializer or JsonSerializer()
            self.cache = cache_backend or get_cache_backend()
            self.metrics = None
            self._logger = None
            return

        super().__init__(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            session_factory=session_factory or SessionLocal,
            serializer=serializer or JsonSerializer(),
            cache_backend=cache_backend or get_cache_backend(),
        )

    async def create_api_key(
        self,
        *,
        name: str,
        scopes: list[str],
        expires_at: datetime | None,
    ) -> ApiKeyIssueResult:
        self._assert_owner_or_admin()

        normalized_name = sanitize_text(name, max_length=120)
        if not normalized_name:
            raise AppError(status_code=400, code="invalid_api_key_name", message="API key name is required")
        normalized_scopes = self._normalize_scopes(scopes)
        if expires_at is not None and expires_at <= datetime.now(UTC):
            raise AppError(status_code=400, code="invalid_api_key_expiry", message="expires_at must be in the future")

        plain_key = self._generate_plain_key()
        hashed = self._hash_key(plain_key)
        lookup_prefix = plain_key[:_LOOKUP_PREFIX_LEN]

        def write_op(db: Session) -> ApiKey:
            repo = ApiKeyRepository(db)
            return repo.create(
                tenant_id=self.tenant_id,
                name=normalized_name,
                key_prefix=lookup_prefix,
                hashed_key=hashed,
                scopes=normalized_scopes,
                expires_at=expires_at,
            )

        entity = await self.execute_write(write_op, idempotent=False)
        await self._invalidate_tenant_cache()
        return ApiKeyIssueResult(api_key=entity, plain_key=plain_key)

    async def list_api_keys(self) -> list[ApiKey]:
        self._assert_owner_or_admin()

        def read_op(db: Session) -> list[ApiKey]:
            repo = ApiKeyRepository(db)
            return repo.list_for_tenant(tenant_id=self.tenant_id, include_revoked=True)

        return await self.execute_read(read_op)

    async def revoke_api_key(self, *, api_key_id: UUID) -> ApiKey:
        self._assert_owner_or_admin()
        now = datetime.now(UTC)

        def write_op(db: Session) -> ApiKey:
            repo = ApiKeyRepository(db)
            entity = repo.revoke(tenant_id=self.tenant_id, api_key_id=api_key_id, revoked_at=now)
            if entity is None:
                raise AppError(status_code=404, code="api_key_not_found", message="API key not found")
            return entity

        entity = await self.execute_write(write_op, idempotent=True)
        await self._invalidate_tenant_cache()
        return entity

    async def authenticate_key(self, *, raw_key: str) -> ApiKeyAuthResult:
        if not raw_key.startswith(_RAW_KEY_PREFIX):
            raise AppError(status_code=401, code="invalid_api_key", message="Invalid API key")

        computed_hash = self._hash_key(raw_key)
        cache_key = f"api_key:auth:{computed_hash}"
        cached = await self._cache_get_auth(cache_key)
        if cached is not None:
            return cached

        lookup_prefix = raw_key[:_LOOKUP_PREFIX_LEN]
        now = datetime.now(UTC)

        def read_op() -> list[ApiKey]:
            with self._session_factory() as session:
                repo = ApiKeyRepository(session)
                return repo.find_candidates_by_prefix(key_prefix=lookup_prefix, now=now)

        candidates = await run_in_threadpool(read_op)
        for candidate in candidates:
            if hmac.compare_digest(candidate.hashed_key, computed_hash):
                if candidate.revoked_at is not None:
                    raise AppError(status_code=401, code="api_key_revoked", message="API key revoked")
                if candidate.expires_at is not None and candidate.expires_at <= now:
                    raise AppError(status_code=401, code="api_key_expired", message="API key expired")
                result = ApiKeyAuthResult(
                    api_key_id=candidate.id,
                    tenant_id=candidate.tenant_id,
                    scopes=self._normalize_scopes(candidate.scopes),
                    name=candidate.name,
                )
                await self._cache_set_auth(cache_key, result)
                await self._touch_last_used(candidate.id)
                return result

        raise AppError(status_code=401, code="invalid_api_key", message="Invalid API key")

    @staticmethod
    def has_scope(*, scopes: list[str], required_scope: str) -> bool:
        required = required_scope.strip().lower()
        if not required:
            return True
        scope_set = {scope.strip().lower() for scope in scopes if scope}
        if "*" in scope_set or required in scope_set:
            return True

        resource = required.split(":", 1)[0]
        if f"{resource}:*" in scope_set:
            return True
        return False

    @staticmethod
    def to_request_context(auth: ApiKeyAuthResult) -> ApiKeyRequestContext:
        return ApiKeyRequestContext(
            api_key_id=auth.api_key_id,
            tenant_id=auth.tenant_id,
            scopes=auth.scopes,
            name=auth.name,
        )

    async def _touch_last_used(self, api_key_id: UUID) -> None:
        now = datetime.now(UTC)

        def write_op() -> None:
            with self._session_factory() as session:
                transaction = session.begin()
                try:
                    repo = ApiKeyRepository(session)
                    repo.update_last_used(api_key_id=api_key_id, last_used_at=now)
                    transaction.commit()
                except Exception:
                    transaction.rollback()
                    raise

        try:
            await run_in_threadpool(write_op)
        except Exception:
            return

    async def _cache_get_auth(self, cache_key: str) -> ApiKeyAuthResult | None:
        try:
            raw = await self.cache.get(cache_key)
            if raw is None:
                return None
            decoded = self.serializer.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(decoded, dict):
                return None
            return ApiKeyAuthResult(
                api_key_id=UUID(str(decoded["api_key_id"])),
                tenant_id=UUID(str(decoded["tenant_id"])),
                scopes=self._normalize_scopes(decoded.get("scopes", [])),
                name=str(decoded.get("name", "")),
            )
        except Exception:
            return None

    async def _cache_set_auth(self, cache_key: str, auth: ApiKeyAuthResult) -> None:
        payload = {
            "api_key_id": str(auth.api_key_id),
            "tenant_id": str(auth.tenant_id),
            "scopes": auth.scopes,
            "name": auth.name,
        }
        try:
            await self.cache.set(cache_key, self.serializer.dumps(payload), self._cache_ttl)
        except Exception:
            return

    async def _invalidate_tenant_cache(self) -> None:
        # Hash-indexed auth cache is short-lived; no wildcard invalidation required.
        return

    def _assert_owner_or_admin(self) -> None:
        if self.actor_role in {"owner", "admin"}:
            return
        raise AppError(status_code=403, code="permission_denied", message="Permission denied")

    @staticmethod
    def _generate_plain_key() -> str:
        token = secrets.token_urlsafe(32).replace("-", "").replace("_", "")
        return f"{_RAW_KEY_PREFIX}{token[:56]}"

    def _hash_key(self, raw_key: str) -> str:
        digest = hashlib.sha256()
        digest.update(self._pepper.encode("utf-8"))
        digest.update(raw_key.encode("utf-8"))
        return digest.hexdigest()

    @staticmethod
    def _normalize_scopes(scopes: list[str] | Any) -> list[str]:
        if not isinstance(scopes, list):
            raise AppError(status_code=400, code="invalid_api_key_scopes", message="Scopes must be an array")
        normalized: list[str] = []
        for raw in scopes:
            scope = str(raw).strip().lower()
            if not scope:
                continue
            if scope == "*":
                normalized.append(scope)
                continue
            if ":" not in scope:
                raise AppError(status_code=400, code="invalid_api_key_scope", message=f"Invalid scope '{scope}'")
            resource, action = scope.split(":", 1)
            if not resource or action not in {"read", "write", "*"}:
                raise AppError(status_code=400, code="invalid_api_key_scope", message=f"Invalid scope '{scope}'")
            normalized.append(f"{resource}:{action}")
        deduped = sorted(set(normalized))
        if not deduped:
            raise AppError(status_code=400, code="invalid_api_key_scopes", message="At least one scope is required")
        return deduped
