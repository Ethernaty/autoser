from __future__ import annotations

from starlette.concurrency import run_in_threadpool

from app.services.auth_service import AuthService, UserContext
from app.services.jwt_service import TokenType, get_jwt_service


async def resolve_user_context(*, auth_service: AuthService, access_token: str) -> UserContext:
    jwt_service = get_jwt_service()
    payload = await jwt_service.decode_async(
        access_token,
        expected_type=TokenType.ACCESS,
        check_revoked=True,
        fail_closed=False,
    )
    return await run_in_threadpool(
        auth_service.me_by_scope,
        user_id=payload.user_id,
        tenant_id=payload.tenant_uuid,
    )
