# core/cache_manager.py
# ══════════════════════════════════════════════════════════════
# CACHE MANAGER
#
# Abstrae el acceso a la cache de Flask para que el resto
# del código no dependa directamente de flask_caching.
#
# En contextos sin Flask (backtest, scripts CLI), se usa
# un dict simple en memoria como sustituto.
# ══════════════════════════════════════════════════════════════

import time
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# CACHE EN MEMORIA (sin Flask)
# ─────────────────────────────────────────────────────────────

class MemoryCache:
    """
    Cache simple en memoria con TTL.
    Sustituto de Flask-Caching para uso en backtest o scripts.
    """

    def __init__(self, timeout: int = 600):
        self._store: dict = {}
        self._default_timeout = timeout

    def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            return None
        value, expires_at = self._store[key]
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, timeout: int = None) -> bool:
        ttl = timeout if timeout is not None else self._default_timeout
        self._store[key] = (value, time.time() + ttl)
        return True

    def delete(self, key: str) -> bool:
        return bool(self._store.pop(key, None))

    def clear(self) -> bool:
        self._store.clear()
        return True

    def get_many(self, *keys) -> dict:
        return {k: self.get(k) for k in keys}

    def set_many(self, mapping: dict, timeout: int = None) -> list:
        failed = []
        for k, v in mapping.items():
            if not self.set(k, v, timeout):
                failed.append(k)
        return failed

    def __repr__(self):
        return f"<MemoryCache {len(self._store)} items>"


# ─────────────────────────────────────────────────────────────
# HELPER PARA USAR INDISTINTAMENTE FLASK-CACHE O MEMORY-CACHE
# ─────────────────────────────────────────────────────────────

def cache_get(cache, key: str) -> Optional[Any]:
    """Lee de cache independientemente del tipo (Flask o Memory)."""
    if cache is None:
        return None
    try:
        return cache.get(key)
    except Exception as e:
        logger.debug(f"cache_get error: {e}")
        return None


def cache_set(cache, key: str, value: Any, timeout: int = 600) -> bool:
    """Escribe en cache independientemente del tipo."""
    if cache is None:
        return False
    try:
        cache.set(key, value, timeout=timeout)
        return True
    except Exception as e:
        logger.debug(f"cache_set error: {e}")
        return False


# Instancia global para uso sin Flask (backtest, tests, CLI)
memory_cache = MemoryCache(timeout=600)
