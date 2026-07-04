"""API Key Manager with automatic rotation and fallback.

Handles multiple API keys for Groq, Gemini, and SerpAPI.
When a key hits rate limits, automatically switches to the next key.
"""

import time
from typing import Optional
from app.config import settings


class KeyManager:
    """Manages multiple API keys with automatic rotation on rate limits."""

    def __init__(self):
        self._keys = {}
        self._current_index = {}
        self._cooldown = {}  # key -> cooldown until timestamp
        self._init_keys()

    def _init_keys(self):
        """Initialize key pools from config."""
        # Groq keys
        groq_keys = [k.strip() for k in settings.groq_api_keys.split(",") if k.strip()]
        if settings.groq_api_key:
            groq_keys.insert(0, settings.groq_api_key)
        self._keys["groq"] = groq_keys
        self._current_index["groq"] = 0

        # Gemini keys
        gemini_keys = [
            k.strip() for k in settings.gemini_api_keys.split(",") if k.strip()
        ]
        if settings.gemini_api_key:
            gemini_keys.insert(0, settings.gemini_api_key)
        self._keys["gemini"] = gemini_keys
        self._current_index["gemini"] = 0

        # SerpAPI keys
        serpapi_keys = [
            k.strip() for k in settings.serpapi_keys.split(",") if k.strip()
        ]
        if settings.serpapi_key:
            serpapi_keys.insert(0, settings.serpapi_key)
        self._keys["serpapi"] = serpapi_keys
        self._current_index["serpapi"] = 0

    def get_key(self, provider: str) -> Optional[str]:
        """Get the current active key for a provider."""
        keys = self._keys.get(provider, [])
        if not keys:
            return None

        idx = self._current_index.get(provider, 0)
        now = time.time()

        # Check if current key is in cooldown
        current_key = keys[idx]
        if current_key in self._cooldown and now < self._cooldown[current_key]:
            # Try next key
            return self._get_next_key(provider)

        return current_key

    def _get_next_key(self, provider: str) -> Optional[str]:
        """Get the next available key, rotating if needed."""
        keys = self._keys.get(provider, [])
        if not keys:
            return None

        idx = self._current_index.get(provider, 0)
        now = time.time()

        # Try all keys
        for _ in range(len(keys)):
            idx = (idx + 1) % len(keys)
            key = keys[idx]
            # Check if this key is available (not in cooldown)
            if key not in self._cooldown or now >= self._cooldown[key]:
                self._current_index[provider] = idx
                return key

        # All keys in cooldown, return the one with shortest cooldown
        min_cooldown_key = min(keys, key=lambda k: self._cooldown.get(k, 0))
        self._current_index[provider] = keys.index(min_cooldown_key)
        return min_cooldown_key

    def mark_rate_limited(
        self, provider: str, key: Optional[str] = None, cooldown_seconds: int = 60
    ):
        """Mark a key as rate-limited. Automatically switches to next key."""
        if key is None:
            key = self.get_key(provider)

        if key:
            self._cooldown[key] = time.time() + cooldown_seconds
            # Auto-rotate to next key
            self._get_next_key(provider)

    def get_status(self) -> dict:
        """Get status of all key pools."""
        status = {}
        for provider, keys in self._keys.items():
            now = time.time()
            available = sum(
                1 for k in keys if k not in self._cooldown or now >= self._cooldown[k]
            )
            status[provider] = {
                "total": len(keys),
                "available": available,
                "current_index": self._current_index.get(provider, 0),
            }
        return status


# Global singleton
key_manager = KeyManager()
