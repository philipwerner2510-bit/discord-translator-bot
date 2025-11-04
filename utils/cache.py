# utils/cache.py
import asyncio
import hashlib
from time import monotonic
from collections import OrderedDict
from typing import Tuple, Optional, Callable, Awaitable

ResultT = Tuple[str, str]  # (translated_text, detected_lang)

class TranslationCache:
    """TTL + size-bounded LRU cache for translation results."""
    def __init__(self, ttl: int = 300, max_entries: int = 2000):
        self.ttl = ttl
        self.max_entries = max_entries
        self._store: "OrderedDict[str, Tuple[ResultT, float]]" = OrderedDict()
        self._lock = asyncio.Lock()

    @staticmethod
    def _key(text: str, target_lang: str) -> str:
        norm = " ".join((text or "").split()).casefold()
        h = hashlib.sha256(norm.encode("utf-8")).hexdigest()
        return f"{h}:{target_lang.lower()}"

    async def get(self, text: str, target_lang: str) -> Optional[ResultT]:
        k = self._key(text, target_lang)
        async with self._lock:
            item = self._store.get(k)
            if not item:
                return None
            value, ts = item
            if monotonic() - ts >= self.ttl:
                self._store.pop(k, None)
                return None
            self._store.move_to_end(k, last=True)
            return value

    async def set(self, text: str, target_lang: str, value: ResultT) -> None:
        k = self._key(text, target_lang)
        async with self._lock:
            self._store[k] = (value, monotonic())
            self._store.move_to_end(k, last=True)
            while len(self._store) > self.max_entries:
                self._store.popitem(last=False)

    async def get_or_set(self, text: str, target_lang: str, compute: Callable[[], Awaitable[ResultT]]) -> ResultT:
        v = await self.get(text, target_lang)
        if v is not None:
            return v
        v = await compute()
        await self.set(text, target_lang, v)
        return v

    async def cleanup(self) -> None:
        async with self._lock:
            now = monotonic()
            ks = [k for k, (_, ts) in self._store.items() if now - ts >= self.ttl]
            for k in ks:
                self._store.pop(k, None)