import asyncio

class TranslationCache:
    def __init__(self, ttl=300):
        self.cache = {}  # (hash(text), lang) -> (translation, detected)
        self.ttl = ttl
        self.lock = asyncio.Lock()

    async def get(self, key):
        async with self.lock:
            return self.cache.get(key)

    async def set(self, key, value):
        async with self.lock:
            self.cache[key] = value
            asyncio.create_task(self._expire(key))

    async def _expire(self, key):
        await asyncio.sleep(self.ttl)
        async with self.lock:
            self.cache.pop(key, None)

cache = TranslationCache()
