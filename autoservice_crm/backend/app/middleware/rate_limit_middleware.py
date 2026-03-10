from __future__ import annotations

import asyncio
import ipaddress
import re
import time
from abc import ABC, abstractmethod
from collections import OrderedDict, deque
from dataclasses import dataclass
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Match

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.prometheus_metrics import get_metrics_registry
from app.core.runtime_guards import assert_bounded_structure


@dataclass
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    reset_seconds: int


class RateLimitStore(ABC):
    @abstractmethod
    async def hit(self, *, key: str, window_seconds: int) -> tuple[int, int]:
        """Register request and return (count, reset_seconds)."""


class InMemoryRateLimitStore(RateLimitStore):
    """Bounded in-memory sliding-window store with periodic cleanup."""

    def __init__(self, *, max_keys: int, cleanup_interval_seconds: int):
        self._events: dict[str, deque[float]] = {}
        self._last_seen: OrderedDict[str, float] = OrderedDict()
        self._max_keys = max(1_000, max_keys)
        self._cleanup_interval = max(5, cleanup_interval_seconds)
        self._last_cleanup = 0.0
        self._lock = asyncio.Lock()

    async def hit(self, *, key: str, window_seconds: int) -> tuple[int, int]:
        now = time.time()
        boundary = now - window_seconds

        async with self._lock:
            if now - self._last_cleanup >= self._cleanup_interval:
                self._cleanup(boundary=boundary, now=now)
                self._last_cleanup = now

            bucket = self._events.setdefault(key, deque())
            while bucket and bucket[0] <= boundary:
                bucket.popleft()
            bucket.append(now)

            self._last_seen[key] = now
            self._last_seen.move_to_end(key)

            self._enforce_max_keys()

            oldest = bucket[0]
            reset_seconds = max(1, int(window_seconds - (now - oldest)))
            return len(bucket), reset_seconds

    def _cleanup(self, *, boundary: float, now: float) -> None:
        stale_keys: list[str] = []
        for key, bucket in self._events.items():
            while bucket and bucket[0] <= boundary:
                bucket.popleft()
            if not bucket:
                stale_keys.append(key)

        for key in stale_keys:
            self._events.pop(key, None)
            self._last_seen.pop(key, None)

        old_keys = [key for key, seen in self._last_seen.items() if now - seen > self._cleanup_interval * 3]
        for key in old_keys:
            self._events.pop(key, None)
            self._last_seen.pop(key, None)

    def _enforce_max_keys(self) -> None:
        while len(self._events) > self._max_keys:
            victim_key, _ = self._last_seen.popitem(last=False)
            self._events.pop(victim_key, None)
        assert_bounded_structure(name="rate_limit_keys", size=len(self._events), limit=self._max_keys)


class RedisRateLimitStore(RateLimitStore):
    """Redis sorted-set sliding-window rate limiter."""

    _HIT_SCRIPT = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, ARGV[1] - ARGV[2])
redis.call('ZADD', KEYS[1], ARGV[1], ARGV[3])
redis.call('EXPIRE', KEYS[1], math.ceil(ARGV[2]))
local count = redis.call('ZCARD', KEYS[1])
local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
local reset = tonumber(ARGV[2])
if oldest[2] then
  reset = math.ceil(tonumber(ARGV[2]) - (tonumber(ARGV[1]) - tonumber(oldest[2])))
  if reset < 1 then reset = 1 end
end
return {count, reset}
""".strip()

    def __init__(self, redis_url: str, key_prefix: str = "crm:rl"):
        try:
            from redis.asyncio import Redis
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("redis dependency is required for RedisRateLimitStore") from exc

        self._redis = Redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        self._key_prefix = key_prefix

    async def hit(self, *, key: str, window_seconds: int) -> tuple[int, int]:
        now = time.time()
        zset_key = f"{self._key_prefix}:{key}"
        window_start = now - window_seconds
        member = f"{now}:{uuid4()}"
        _ = window_start
        result = await self._redis.eval(
            self._HIT_SCRIPT,
            1,
            zset_key,
            str(now),
            str(float(window_seconds)),
            member,
        )
        count = int(result[0])
        reset_seconds = int(result[1])
        return count, reset_seconds


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Tenant/user-aware sliding-window rate limiter."""

    EXEMPT_PATHS = {
        "/health",
        "/health/live",
        "/health/ready",
        "/health/deps",
        "/metrics",
        "/docs",
        "/docs/oauth2-redirect",
        "/openapi.json",
        "/redoc",
    }

    _UUID_OR_INT_SEGMENT = re.compile(r"^([0-9]+|[0-9a-fA-F-]{32,36})$")

    def __init__(self, app):
        super().__init__(app)
        settings = get_settings()
        self._enabled = settings.rate_limit_enabled
        self._window_seconds = settings.rate_limit_window_seconds
        self._per_user_limit = settings.rate_limit_per_user
        self._per_ip_limit = settings.rate_limit_per_ip
        self._burst_tolerance = max(0, settings.rate_limit_burst_tolerance)
        self._metrics = get_metrics_registry()

        self._trusted_proxies = {
            ip.strip() for ip in settings.trusted_proxy_ips.split(",") if ip.strip()
        }

        if settings.rate_limit_backend == "redis":
            try:
                self._store = RedisRateLimitStore(
                    redis_url=settings.redis_url,
                    key_prefix=settings.rate_limit_redis_prefix,
                )
            except Exception:
                self._store = InMemoryRateLimitStore(
                    max_keys=settings.rate_limit_memory_max_keys,
                    cleanup_interval_seconds=settings.rate_limit_cleanup_interval_seconds,
                )
        else:
            self._store = InMemoryRateLimitStore(
                max_keys=settings.rate_limit_memory_max_keys,
                cleanup_interval_seconds=settings.rate_limit_cleanup_interval_seconds,
            )

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self._enabled or request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        identifier, identifier_type, limit = self._resolve_identifier(request)
        route_key = self._resolve_route_key(request)
        scope_key = f"{identifier}:{request.method}:{route_key}"
        count, reset_seconds = await self._store.hit(key=scope_key, window_seconds=self._window_seconds)
        effective_limit = limit + self._burst_tolerance

        if count > effective_limit:
            self._metrics.increment_rate_limit_rejection(route=route_key, identifier_type=identifier_type)
            error = AppError(
                status_code=429,
                code="rate_limit_exceeded",
                message="Rate limit exceeded",
                details={"limit": effective_limit, "reset_seconds": reset_seconds},
            )
            response = JSONResponse(status_code=error.status_code, content=error.to_dict())
            self._apply_headers(response, limit=effective_limit, remaining=0, reset_seconds=reset_seconds)
            return response

        remaining = max(0, effective_limit - count)
        response = await call_next(request)
        self._apply_headers(response, limit=effective_limit, remaining=remaining, reset_seconds=reset_seconds)
        return response

    def _resolve_identifier(self, request: Request) -> tuple[str, str, int]:
        user_context = getattr(request.state, "user_context", None)
        if user_context is not None:
            return (
                f"tenant:{user_context.tenant_id}:principal:{user_context.user_id}",
                "user",
                self._per_user_limit,
            )

        fallback_tenant = getattr(getattr(request.state, "api_key_context", None), "tenant_id", None)
        if fallback_tenant is not None:
            return (
                f"tenant:{fallback_tenant}:ip:{self._resolve_client_ip(request)}",
                "ip",
                self._per_ip_limit,
            )
        return f"ip:{self._resolve_client_ip(request)}", "ip", self._per_ip_limit

    def _resolve_client_ip(self, request: Request) -> str:
        client = request.client
        remote_ip = client.host if client else "unknown"

        forwarded_for = request.headers.get("X-Forwarded-For")
        if not forwarded_for:
            return remote_ip

        if not self._is_trusted_proxy(remote_ip):
            return remote_ip

        parts = [segment.strip() for segment in forwarded_for.split(",") if segment.strip()]
        if not parts:
            return remote_ip

        candidate = parts[0]
        try:
            ipaddress.ip_address(candidate)
            return candidate
        except ValueError:
            return remote_ip

    def _is_trusted_proxy(self, remote_ip: str) -> bool:
        if remote_ip in self._trusted_proxies:
            return True
        try:
            parsed = ipaddress.ip_address(remote_ip)
        except ValueError:
            return False

        for trusted in self._trusted_proxies:
            try:
                network = ipaddress.ip_network(trusted, strict=False)
                if parsed in network:
                    return True
            except ValueError:
                continue
        return False

    def _resolve_route_key(self, request: Request) -> str:
        route = request.scope.get("route")
        if route is not None and hasattr(route, "path"):
            path = str(route.path)
            if path:
                return path

        for route in request.app.router.routes:
            try:
                match, _ = route.matches(request.scope)
            except Exception:
                continue
            if match == Match.FULL and hasattr(route, "path"):
                template = str(route.path)
                if template:
                    return template

        segments = []
        for segment in request.url.path.split("/"):
            if self._UUID_OR_INT_SEGMENT.match(segment):
                segments.append("{id}")
            else:
                segments.append(segment)
        return "/".join(segments)

    @staticmethod
    def _apply_headers(response: Response, *, limit: int, remaining: int, reset_seconds: int) -> None:
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_seconds)
