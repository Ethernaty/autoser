from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel, Field

from app.core.internal_auth import require_internal_service_auth
from app.security_validation.service import SecurityValidationService


router = APIRouter(
    prefix="/internal",
    tags=["Internal Security"],
    dependencies=[Depends(require_internal_service_auth)],
)


class SecurityReportResponse(BaseModel):
    ATTACK_RESULTS: dict = Field(default_factory=dict)
    VULNERABILITIES: dict = Field(default_factory=dict)
    RISK_SCORE: dict = Field(default_factory=dict)
    EXPLOIT_PATHS: dict = Field(default_factory=dict)
    REMEDIATION: list[dict] = Field(default_factory=list)
    TELEMETRY: dict = Field(default_factory=dict)
    GENERATED_AT_UNIX: float


@lru_cache(maxsize=1)
def get_security_validation_service() -> SecurityValidationService:
    return SecurityValidationService()


@router.get("/security-report", response_model=SecurityReportResponse)
async def internal_security_report(
    request: Request,
    refresh: bool = Query(default=False),
    jwt_tokens_header: str | None = Header(default=None, alias="X-Security-JWT"),
    api_keys_header: str | None = Header(default=None, alias="X-Security-API-Key"),
    service: SecurityValidationService = Depends(get_security_validation_service),
) -> SecurityReportResponse:
    jwt_tokens = _parse_csv_header(jwt_tokens_header)
    api_keys = _parse_csv_header(api_keys_header)
    report = await service.get_or_run(
        base_url=str(request.base_url).rstrip("/"),
        jwt_tokens=jwt_tokens,
        api_keys=api_keys,
        force_refresh=bool(refresh),
    )
    payload = report.to_dict()
    return SecurityReportResponse(
        ATTACK_RESULTS=payload["attack_results"],
        VULNERABILITIES=payload["vulnerabilities"],
        RISK_SCORE=payload["risk_score"],
        EXPLOIT_PATHS=payload["exploit_paths"],
        REMEDIATION=payload["remediation"],
        TELEMETRY=payload["telemetry"],
        GENERATED_AT_UNIX=float(payload["generated_at_unix"]),
    )


def _parse_csv_header(value: str | None) -> tuple[str, ...]:
    if value is None:
        return ()
    parts = [item.strip() for item in value.split(",") if item.strip()]
    return tuple(parts)
