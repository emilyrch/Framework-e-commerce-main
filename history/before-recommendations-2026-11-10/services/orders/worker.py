import asyncio
from contextlib import suppress


class RecoveryWorker:
    def __init__(self, checkout):
        self.checkout, self.task, self.healthy = checkout, None, True

    def start(self):
        self.task = asyncio.create_task(self.run(), name='order-recovery')

    async def run(self):
        while True:
            try:
                await self.checkout.recover_batch()
                self.healthy = True
            except Exception:
                # No tokens, bodies, addresses or exception details in logs/readiness.
                self.healthy = False
            await asyncio.sleep(0.5)

    @property
    def ready(self):
        return self.task is not None and not self.task.done() and self.healthy

    async def close(self):
        if self.task:
            self.task.cancel()
            with suppress(asyncio.CancelledError): await self.task
