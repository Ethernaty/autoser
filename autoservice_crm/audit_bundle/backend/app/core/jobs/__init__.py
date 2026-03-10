from functools import lru_cache

from app.core.cache import get_cache_backend
from app.core.config import get_settings
from app.core.jobs.job_queue import InMemoryJobQueue, JobQueue
from app.core.jobs.kafka_queue_adapter import KafkaQueueAdapter
from app.core.jobs.redis_queue_adapter import RedisQueueAdapter
from app.core.jobs.task_registry import TaskRegistry, default_task_registry, task
from app.core.jobs.worker import JobWorker


@lru_cache(maxsize=1)
def get_job_queue() -> JobQueue:
    settings = get_settings()
    backend = settings.job_queue_backend
    if backend == "redis":
        try:
            return RedisQueueAdapter(
                redis_url=settings.redis_url,
                namespace=settings.job_queue_namespace,
                visibility_timeout_seconds=settings.job_queue_visibility_timeout_seconds,
            )
        except Exception:
            return InMemoryJobQueue()
    if backend == "kafka":
        try:
            return KafkaQueueAdapter(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                topic=settings.kafka_job_topic,
                dead_letter_topic=settings.kafka_job_dlq_topic,
                consumer_group=settings.job_queue_consumer_group,
            )
        except Exception:
            return InMemoryJobQueue()
    return InMemoryJobQueue()


@lru_cache(maxsize=1)
def get_task_registry() -> TaskRegistry:
    return default_task_registry


@lru_cache(maxsize=1)
def get_job_worker() -> JobWorker:
    settings = get_settings()
    return JobWorker(
        queue=get_job_queue(),
        registry=get_task_registry(),
        poll_timeout_seconds=settings.job_queue_poll_timeout_seconds,
        cache_backend=get_cache_backend(),
    )


__all__ = ["TaskRegistry", "task", "get_job_queue", "get_task_registry", "get_job_worker"]
