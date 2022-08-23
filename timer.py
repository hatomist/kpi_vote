import asyncio


class Timer:
    def __init__(self, timeout, callback, infinite=False, immediate=False, opts=()):
        self._timeout = timeout
        self._callback = callback
        self._infinite = infinite
        self._task = asyncio.ensure_future(self._job())
        self._immediate = immediate
        self._opts = opts

    async def _job(self):
        if self._immediate:
            await self._callback(*self._opts)
        if not self._infinite and not self._immediate:
            await asyncio.sleep(self._timeout)
            await self._callback
        while self._infinite:
            await asyncio.sleep(self._timeout)
            await self._callback(*self._opts)

    def cancel(self):
        self._infinite = False
        self._task.cancel()
