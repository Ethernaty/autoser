from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="AutoService SaaS CRM", alias="APP_NAME")
    app_env: str = Field(default="production", alias="APP_ENV")
    app_debug: bool = Field(default=False, alias="APP_DEBUG")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")

    database_url: str = Field(..., alias="DATABASE_URL")
    sqlalchemy_echo: bool = Field(default=False, alias="SQLALCHEMY_ECHO")
    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")
    db_pool_recycle_seconds: int = Field(default=1800, alias="DB_POOL_RECYCLE_SECONDS")
    db_pool_timeout_seconds: int = Field(default=30, alias="DB_POOL_TIMEOUT_SECONDS")
    db_timeout_seconds: float = Field(default=5.0, alias="DB_TIMEOUT_SECONDS")
    db_retry_attempts: int = Field(default=3, alias="DB_RETRY_ATTEMPTS")
    db_retry_base_delay_seconds: float = Field(default=0.1, alias="DB_RETRY_BASE_DELAY_SECONDS")
    slow_query_threshold_ms: float = Field(default=250.0, alias="SLOW_QUERY_THRESHOLD_MS")

    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expires_minutes: int = Field(default=15, alias="ACCESS_TOKEN_EXPIRES_MINUTES")
    refresh_token_expires_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRES_DAYS")

    redis_url: str = Field(..., alias="REDIS_URL")

    cache_backend: str = Field(default="redis", alias="CACHE_BACKEND")
    cache_key_prefix: str = Field(default="autoservice", alias="CACHE_KEY_PREFIX")
    client_cache_ttl_seconds: int = Field(default=60, alias="CLIENT_CACHE_TTL_SECONDS")
    client_cache_soft_ttl_seconds: int = Field(default=20, alias="CLIENT_CACHE_SOFT_TTL_SECONDS")
    client_cache_early_refresh_probability: float = Field(default=0.15, alias="CLIENT_CACHE_EARLY_REFRESH_PROBABILITY")
    negative_cache_ttl_seconds: int = Field(default=15, alias="NEGATIVE_CACHE_TTL_SECONDS")
    max_limit: int = Field(default=50, alias="MAX_LIMIT")

    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_backend: str = Field(default="redis", alias="RATE_LIMIT_BACKEND")
    rate_limit_per_user: int = Field(default=120, alias="RATE_LIMIT_PER_USER")
    rate_limit_per_ip: int = Field(default=60, alias="RATE_LIMIT_PER_IP")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")
    rate_limit_memory_max_keys: int = Field(default=10_000, alias="RATE_LIMIT_MEMORY_MAX_KEYS")
    rate_limit_cleanup_interval_seconds: int = Field(default=30, alias="RATE_LIMIT_CLEANUP_INTERVAL_SECONDS")
    trusted_proxy_ips: str = Field(default="127.0.0.1,::1", alias="TRUSTED_PROXY_IPS")
    membership_cache_ttl_seconds: int = Field(default=30, alias="MEMBERSHIP_CACHE_TTL_SECONDS")
    json_max_depth: int = Field(default=12, alias="JSON_MAX_DEPTH")
    forbidden_write_fields: str = Field(
        default="id,tenant_id,created_at,updated_at,deleted_at,password_hash,is_active,version",
        alias="FORBIDDEN_WRITE_FIELDS",
    )
    memory_cache_max_items: int = Field(default=50_000, alias="MEMORY_CACHE_MAX_ITEMS")
    max_singleflight_locks: int = Field(default=4096, alias="MAX_SINGLEFLIGHT_LOCKS")
    billing_cache_ttl_seconds: int = Field(default=60, alias="BILLING_CACHE_TTL_SECONDS")
    tenant_state_cache_ttl_seconds: int = Field(default=30, alias="TENANT_STATE_CACHE_TTL_SECONDS")
    default_trial_days: int = Field(default=14, alias="DEFAULT_TRIAL_DAYS")
    default_plan_name: str = Field(default="starter", alias="DEFAULT_PLAN_NAME")
    usage_default_hard_limit: int = Field(default=10_000, alias="USAGE_DEFAULT_HARD_LIMIT")
    usage_default_burst_limit: int = Field(default=200, alias="USAGE_DEFAULT_BURST_LIMIT")
    usage_warning_ratio: float = Field(default=0.8, alias="USAGE_WARNING_RATIO")
    quota_exceeded_status_code: int = Field(default=402, alias="QUOTA_EXCEEDED_STATUS_CODE")
    internal_service_auth_header: str = Field(default="X-Internal-Service-Auth", alias="INTERNAL_SERVICE_AUTH_HEADER")
    internal_service_auth_key: str = Field(..., alias="INTERNAL_SERVICE_AUTH_KEY")
    api_key_secret_pepper: str = Field(..., alias="API_KEY_SECRET_PEPPER")
    external_api_rate_limit_per_key: int = Field(default=300, alias="EXTERNAL_API_RATE_LIMIT_PER_KEY")
    external_api_rate_limit_window_seconds: int = Field(default=60, alias="EXTERNAL_API_RATE_LIMIT_WINDOW_SECONDS")
    webhook_max_attempts: int = Field(default=5, alias="WEBHOOK_MAX_ATTEMPTS")
    webhook_retry_base_seconds: int = Field(default=2, alias="WEBHOOK_RETRY_BASE_SECONDS")
    webhook_timeout_seconds: float = Field(default=5.0, alias="WEBHOOK_TIMEOUT_SECONDS")
    webhook_internal_http_retries: int = Field(default=2, alias="WEBHOOK_INTERNAL_HTTP_RETRIES")
    webhook_http_max_connections: int = Field(default=200, alias="WEBHOOK_HTTP_MAX_CONNECTIONS")
    webhook_http_max_keepalive: int = Field(default=50, alias="WEBHOOK_HTTP_MAX_KEEPALIVE")
    webhook_dispatch_concurrency: int = Field(default=100, alias="WEBHOOK_DISPATCH_CONCURRENCY")

    job_queue_backend: str = Field(default="redis", alias="JOB_QUEUE_BACKEND")
    job_queue_namespace: str = Field(default="crm:jobs", alias="JOB_QUEUE_NAMESPACE")
    job_queue_visibility_timeout_seconds: int = Field(default=30, alias="JOB_QUEUE_VISIBILITY_TIMEOUT_SECONDS")
    job_queue_poll_timeout_seconds: float = Field(default=1.0, alias="JOB_QUEUE_POLL_TIMEOUT_SECONDS")
    job_queue_consumer_group: str = Field(default="crm-job-workers", alias="JOB_QUEUE_CONSUMER_GROUP")
    kafka_bootstrap_servers: str = Field(default="localhost:9092", alias="KAFKA_BOOTSTRAP_SERVERS")
    kafka_job_topic: str = Field(default="crm.jobs", alias="KAFKA_JOB_TOPIC")
    kafka_job_dlq_topic: str = Field(default="crm.jobs.dlq", alias="KAFKA_JOB_DLQ_TOPIC")
    kafka_event_topic: str = Field(default="crm.events", alias="KAFKA_EVENT_TOPIC")
    kafka_security_protocol: str = Field(default="PLAINTEXT", alias="KAFKA_SECURITY_PROTOCOL")

    rate_limit_burst_tolerance: int = Field(default=20, alias="RATE_LIMIT_BURST_TOLERANCE")
    rate_limit_redis_prefix: str = Field(default="crm:rl", alias="RATE_LIMIT_REDIS_PREFIX")

    event_stream_backend: str = Field(default="kafka", alias="EVENT_STREAM_BACKEND")

    tracing_enabled: bool = Field(default=True, alias="TRACING_ENABLED")
    tracing_exporter: str = Field(default="console", alias="TRACING_EXPORTER")
    tracing_service_name: str = Field(default="autoservice-crm-backend", alias="TRACING_SERVICE_NAME")

    shutdown_drain_timeout_seconds: float = Field(default=20.0, alias="SHUTDOWN_DRAIN_TIMEOUT_SECONDS")
    shutdown_force_exit_timeout_seconds: float = Field(default=30.0, alias="SHUTDOWN_FORCE_EXIT_TIMEOUT_SECONDS")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    max_payload_bytes: int = Field(default=1_048_576, alias="MAX_PAYLOAD_BYTES")
    service_rate_limit_per_minute: int = Field(default=300, alias="SERVICE_RATE_LIMIT_PER_MINUTE")
    idempotency_ttl_seconds: int = Field(default=300, alias="IDEMPOTENCY_TTL_SECONDS")

    @field_validator("app_env")
    @classmethod
    def validate_env(cls, value: str) -> str:
        allowed = {"development", "staging", "production", "test"}
        normalized = value.strip().lower()
        if normalized not in allowed:
            raise ValueError("APP_ENV must be one of development, staging, production, test")
        return normalized

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        normalized = value.strip().upper()
        if normalized not in allowed:
            raise ValueError("LOG_LEVEL must be one of CRITICAL, ERROR, WARNING, INFO, DEBUG")
        return normalized

    @field_validator("cache_backend")
    @classmethod
    def validate_cache_backend(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"redis", "memory"}:
            raise ValueError("CACHE_BACKEND must be redis or memory")
        return normalized

    @field_validator("rate_limit_backend")
    @classmethod
    def validate_rate_limit_backend(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"redis", "memory"}:
            raise ValueError("RATE_LIMIT_BACKEND must be redis or memory")
        return normalized

    @field_validator("job_queue_backend")
    @classmethod
    def validate_job_queue_backend(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"memory", "redis", "kafka"}:
            raise ValueError("JOB_QUEUE_BACKEND must be memory, redis, or kafka")
        return normalized

    @field_validator("event_stream_backend")
    @classmethod
    def validate_event_stream_backend(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"memory", "kafka"}:
            raise ValueError("EVENT_STREAM_BACKEND must be memory or kafka")
        return normalized

    @field_validator("tracing_exporter")
    @classmethod
    def validate_tracing_exporter(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"console", "otlp", "none"}:
            raise ValueError("TRACING_EXPORTER must be console, otlp, or none")
        return normalized

    @model_validator(mode="after")
    def validate_ranges_and_security(self) -> "Settings":
        if self.app_debug:
            raise ValueError("APP_DEBUG=true is forbidden in this deployment profile")

        weak_values = {
            "change-this-secret-in-production",
            "secret",
            "password",
            "changeme",
            "test",
        }
        if len(self.jwt_secret_key.strip()) < 32 or self.jwt_secret_key.strip().lower() in weak_values:
            raise ValueError("JWT_SECRET_KEY is too weak; use at least 32 random characters")

        if self.access_token_expires_minutes <= 0 or self.access_token_expires_minutes > 120:
            raise ValueError("ACCESS_TOKEN_EXPIRES_MINUTES must be in range 1..120")
        if self.refresh_token_expires_days <= 0 or self.refresh_token_expires_days > 60:
            raise ValueError("REFRESH_TOKEN_EXPIRES_DAYS must be in range 1..60")

        if self.db_pool_size <= 0:
            raise ValueError("DB_POOL_SIZE must be > 0")
        if self.db_max_overflow < 0:
            raise ValueError("DB_MAX_OVERFLOW must be >= 0")
        if self.db_pool_timeout_seconds <= 0:
            raise ValueError("DB_POOL_TIMEOUT_SECONDS must be > 0")

        if self.db_timeout_seconds <= 0:
            raise ValueError("DB_TIMEOUT_SECONDS must be > 0")
        if self.db_retry_attempts < 1 or self.db_retry_attempts > 10:
            raise ValueError("DB_RETRY_ATTEMPTS must be in range 1..10")
        if self.db_retry_base_delay_seconds <= 0:
            raise ValueError("DB_RETRY_BASE_DELAY_SECONDS must be > 0")
        if self.slow_query_threshold_ms <= 0:
            raise ValueError("SLOW_QUERY_THRESHOLD_MS must be > 0")

        if self.max_limit <= 0 or self.max_limit > 500:
            raise ValueError("MAX_LIMIT must be in range 1..500")
        if self.max_payload_bytes < 1024 or self.max_payload_bytes > 20 * 1024 * 1024:
            raise ValueError("MAX_PAYLOAD_BYTES must be in range 1024..20971520")

        if self.rate_limit_per_user <= 0:
            raise ValueError("RATE_LIMIT_PER_USER must be > 0")
        if self.rate_limit_per_ip <= 0:
            raise ValueError("RATE_LIMIT_PER_IP must be > 0")
        if self.rate_limit_window_seconds <= 0:
            raise ValueError("RATE_LIMIT_WINDOW_SECONDS must be > 0")
        if self.rate_limit_memory_max_keys < 1000:
            raise ValueError("RATE_LIMIT_MEMORY_MAX_KEYS must be >= 1000")
        if self.rate_limit_cleanup_interval_seconds < 5:
            raise ValueError("RATE_LIMIT_CLEANUP_INTERVAL_SECONDS must be >= 5")

        if self.membership_cache_ttl_seconds < 5 or self.membership_cache_ttl_seconds > 600:
            raise ValueError("MEMBERSHIP_CACHE_TTL_SECONDS must be in range 5..600")
        if self.idempotency_ttl_seconds < 60:
            raise ValueError("IDEMPOTENCY_TTL_SECONDS must be >= 60")
        if self.json_max_depth < 2 or self.json_max_depth > 64:
            raise ValueError("JSON_MAX_DEPTH must be in range 2..64")
        if self.memory_cache_max_items < 1000:
            raise ValueError("MEMORY_CACHE_MAX_ITEMS must be >= 1000")
        if self.max_singleflight_locks < 128:
            raise ValueError("MAX_SINGLEFLIGHT_LOCKS must be >= 128")
        if self.billing_cache_ttl_seconds < 5 or self.billing_cache_ttl_seconds > 3600:
            raise ValueError("BILLING_CACHE_TTL_SECONDS must be in range 5..3600")
        if self.tenant_state_cache_ttl_seconds < 5 or self.tenant_state_cache_ttl_seconds > 600:
            raise ValueError("TENANT_STATE_CACHE_TTL_SECONDS must be in range 5..600")
        if self.default_trial_days < 0 or self.default_trial_days > 60:
            raise ValueError("DEFAULT_TRIAL_DAYS must be in range 0..60")
        if not self.default_plan_name.strip():
            raise ValueError("DEFAULT_PLAN_NAME must not be empty")
        if self.usage_default_hard_limit < 1:
            raise ValueError("USAGE_DEFAULT_HARD_LIMIT must be > 0")
        if self.usage_default_burst_limit < 1:
            raise ValueError("USAGE_DEFAULT_BURST_LIMIT must be > 0")
        if self.usage_warning_ratio <= 0 or self.usage_warning_ratio >= 1:
            raise ValueError("USAGE_WARNING_RATIO must be in range (0, 1)")
        if self.quota_exceeded_status_code not in {402, 429}:
            raise ValueError("QUOTA_EXCEEDED_STATUS_CODE must be 402 or 429")
        if len(self.internal_service_auth_header.strip()) < 3:
            raise ValueError("INTERNAL_SERVICE_AUTH_HEADER must be at least 3 characters")
        if len(self.internal_service_auth_key.strip()) < 32:
            raise ValueError("INTERNAL_SERVICE_AUTH_KEY must be at least 32 characters")
        if len(self.api_key_secret_pepper.strip()) < 32:
            raise ValueError("API_KEY_SECRET_PEPPER must be at least 32 characters")
        if self.external_api_rate_limit_per_key <= 0:
            raise ValueError("EXTERNAL_API_RATE_LIMIT_PER_KEY must be > 0")
        if self.external_api_rate_limit_window_seconds <= 0:
            raise ValueError("EXTERNAL_API_RATE_LIMIT_WINDOW_SECONDS must be > 0")
        if self.webhook_max_attempts < 1 or self.webhook_max_attempts > 20:
            raise ValueError("WEBHOOK_MAX_ATTEMPTS must be in range 1..20")
        if self.webhook_retry_base_seconds < 1 or self.webhook_retry_base_seconds > 300:
            raise ValueError("WEBHOOK_RETRY_BASE_SECONDS must be in range 1..300")
        if self.webhook_timeout_seconds <= 0 or self.webhook_timeout_seconds > 120:
            raise ValueError("WEBHOOK_TIMEOUT_SECONDS must be in range (0, 120]")
        if self.webhook_internal_http_retries < 0 or self.webhook_internal_http_retries > 5:
            raise ValueError("WEBHOOK_INTERNAL_HTTP_RETRIES must be in range 0..5")
        if self.webhook_http_max_connections < 10:
            raise ValueError("WEBHOOK_HTTP_MAX_CONNECTIONS must be >= 10")
        if self.webhook_http_max_keepalive < 1:
            raise ValueError("WEBHOOK_HTTP_MAX_KEEPALIVE must be >= 1")
        if self.webhook_dispatch_concurrency < 1:
            raise ValueError("WEBHOOK_DISPATCH_CONCURRENCY must be >= 1")

        if self.job_queue_visibility_timeout_seconds < 5:
            raise ValueError("JOB_QUEUE_VISIBILITY_TIMEOUT_SECONDS must be >= 5")
        if self.job_queue_poll_timeout_seconds <= 0:
            raise ValueError("JOB_QUEUE_POLL_TIMEOUT_SECONDS must be > 0")
        if not self.job_queue_namespace.strip():
            raise ValueError("JOB_QUEUE_NAMESPACE must not be empty")
        if not self.kafka_bootstrap_servers.strip():
            raise ValueError("KAFKA_BOOTSTRAP_SERVERS must not be empty")
        if not self.kafka_job_topic.strip():
            raise ValueError("KAFKA_JOB_TOPIC must not be empty")
        if not self.kafka_job_dlq_topic.strip():
            raise ValueError("KAFKA_JOB_DLQ_TOPIC must not be empty")
        if not self.kafka_event_topic.strip():
            raise ValueError("KAFKA_EVENT_TOPIC must not be empty")

        if self.rate_limit_burst_tolerance < 0:
            raise ValueError("RATE_LIMIT_BURST_TOLERANCE must be >= 0")
        if not self.rate_limit_redis_prefix.strip():
            raise ValueError("RATE_LIMIT_REDIS_PREFIX must not be empty")

        if not self.tracing_service_name.strip():
            raise ValueError("TRACING_SERVICE_NAME must not be empty")

        if self.shutdown_drain_timeout_seconds <= 0:
            raise ValueError("SHUTDOWN_DRAIN_TIMEOUT_SECONDS must be > 0")
        if self.shutdown_force_exit_timeout_seconds < self.shutdown_drain_timeout_seconds:
            raise ValueError("SHUTDOWN_FORCE_EXIT_TIMEOUT_SECONDS must be >= SHUTDOWN_DRAIN_TIMEOUT_SECONDS")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
