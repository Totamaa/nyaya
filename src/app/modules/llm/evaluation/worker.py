from __future__ import annotations

import asyncio
from collections.abc import Sequence

from app.core.config.logs import get_logger
from .models import MessageEvaluationInput, PersistedEvaluationRecord
from .service import MessageEvaluationService

logger = get_logger()
_TAG = "LLM:EvalWorker"


class AsyncMessageEvaluationWorker:
    def __init__(
        self,
        service: MessageEvaluationService,
        *,
        concurrency: int = 4,
    ) -> None:
        if concurrency < 1:
            raise ValueError("`concurrency` doit être >= 1.")
        self.service = service
        self.concurrency = concurrency

    async def process_batch(
        self,
        requests: Sequence[MessageEvaluationInput],
    ) -> list[PersistedEvaluationRecord]:
        total = len(requests)
        logger.info(_TAG, f"Starting batch", extra=f"total={total} concurrency={self.concurrency}")

        queue: asyncio.Queue[MessageEvaluationInput | None] = asyncio.Queue()
        for request in requests:
            await queue.put(request)
        for _ in range(self.concurrency):
            await queue.put(None)

        results: list[PersistedEvaluationRecord] = []
        results_lock = asyncio.Lock()

        async def consume() -> None:
            while True:
                item = await queue.get()
                try:
                    if item is None:
                        return
                    record = await asyncio.to_thread(self.service.process, item)
                    async with results_lock:
                        results.append(record)
                finally:
                    queue.task_done()

        workers = [asyncio.create_task(consume()) for _ in range(self.concurrency)]
        await queue.join()
        await asyncio.gather(*workers)

        success = sum(1 for r in results if r.status == "success")
        logger.info(_TAG, f"Batch done", extra=f"success={success}/{total}")
        return results
