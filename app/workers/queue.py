"""
Background Queue and Task Dispatcher.
Supports Redis Queue when configured, with seamless in-memory asyncio fallback.
"""
import asyncio
from typing import Callable, Any, Dict, Optional
import json

from app.config import settings
from app.utils.logger import logger

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class TaskQueueManager:
    def __init__(self):
        self.redis_client = None
        self._async_queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        self._handlers: Dict[str, Callable] = {}
        self._is_running = False

    async def initialize(self):
        """Initializes connection to Redis or starts in-memory background worker."""
        if settings.redis_url and REDIS_AVAILABLE:
            try:
                self.redis_client = aioredis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                await self.redis_client.ping()
                logger.info("Connected to Redis background queue.")
            except Exception as e:
                logger.warning(f"Could not connect to Redis ({e}). Falling back to in-memory asyncio queue.")
                self.redis_client = None

        self._is_running = True
        self._worker_task = asyncio.create_task(self._in_memory_worker_loop())
        logger.info("Background task processor started.")

    def register_handler(self, task_name: str, handler: Callable):
        """Registers a handler function for a task name."""
        self._handlers[task_name] = handler

    async def enqueue(self, task_name: str, payload: Dict[str, Any]):
        """Dispatches a task to background execution."""
        data = {"task": task_name, "payload": payload}
        if self.redis_client:
            try:
                await self.redis_client.rpush("unicon_ai_jobs", json.dumps(data))
                return
            except Exception as e:
                logger.error(f"Redis enqueue failed: {e}. Using in-memory fallback.")

        await self._async_queue.put(data)

    async def _in_memory_worker_loop(self):
        """Processes background tasks sequentially or concurrently without blocking the main event loop."""
        while self._is_running:
            try:
                data = await self._async_queue.get()
                task_name = data.get("task")
                payload = data.get("payload", {})
                handler = self._handlers.get(task_name)
                
                if handler:
                    try:
                        await handler(payload)
                    except Exception as e:
                        logger.error(f"Error executing background task '{task_name}': {e}", exc_info=True)
                else:
                    logger.warning(f"No handler registered for background task '{task_name}'")
                
                self._async_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Background worker loop error: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def shutdown(self):
        """Gracefully stops background queue."""
        self._is_running = False
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
        if self.redis_client:
            await self.redis_client.close()
        logger.info("Background task processor shut down.")


task_queue = TaskQueueManager()
