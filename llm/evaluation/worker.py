from __future__ import annotations

import asyncio
from collections.abc import Sequence

from .models import MessageEvaluationInput, PersistedEvaluationRecord
from .service import MessageEvaluationService


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
        return results
