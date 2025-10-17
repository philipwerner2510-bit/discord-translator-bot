import asyncio
import time

class TranslationCache:
    """
    A simple in-memory cache for translations with TTL (time-to-live).
    Prevents repeated calls to translation APIs for the same text/language.
    """

    def __init__(self, ttl: int = 300):
        """
        Parameters:
        - ttl: time-to-live in seconds for cached entries
        """
        self.ttl = ttl
        self.cache = {}  # key: (text, target_lang), value: (translation, timestamp)
        self.lock = asyncio.Lock()

    async def get(self, text: str, target_lang: str):
        """
        Returns cached translation if exists and not expired, else None.
        """
        key = (text, target_lang)
        async with self.lock:
            if key in self.cache:
                translation, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    return translation
                else:
                    # expired
                    del self.cache[key]
            return None

    async def set(self, text: str, target_lang: str, translation: str):
        """
        Stores a translation in the cache.
        """
        key = (text, target_lang)
        async with self.lock:
            self.cache[key] = (translation, time.time())

    async def clear(self):
        """
        Clears the entire cache.
        """
        async with self.lock:
            self.cache.clear()

    async def cleanup(self):
        """
        Removes expired entries from cache.
        """
        async with self.lock:
            now = time.time()
            keys_to_delete = [key for key, (_, ts) in self.cache.items() if now - ts >= self.ttl]
            for key in keys_to_delete:
                del self.cache[key]
