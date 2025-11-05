# utils/cache.py
import asyncio, time

class TranslationCache:
    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self.cache = {}  # (text, lang) -> (value, ts)
        self.lock = asyncio.Lock()

    async def get(self, text: str, target_lang: str):
        key = (text, target_lang)
        async with self.lock:
            v = self.cache.get(key)
            if not v:
                return None
            value, ts = v
            if time.time() - ts < self.ttl:
                return value
            self.cache.pop(key, None)
            return None

    async def set(self, text: str, target_lang: str, translation: str):
        key = (text, target_lang)
        async with self.lock:
            self.cache[key] = (translation, time.time())

    async def clear(self):
        async with self.lock:
            self.cache.clear()
