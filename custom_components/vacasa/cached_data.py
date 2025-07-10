"""Caching utilities for the Vacasa integration."""

import asyncio
import json
import logging
import os
import random
import time
from typing import Any, TypeVar

from .const import DEFAULT_CACHE_TTL, PROPERTY_CACHE_FILE

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


class CachedData:
    """Manages cached data with TTL (Time To Live) support."""

    def __init__(
        self,
        cache_file_path: str | None = None,
        default_ttl: int = DEFAULT_CACHE_TTL,
        hass=None,
    ) -> None:
        """Initialize the cached data manager.

        Args:
            cache_file_path: Optional path to cache file
            default_ttl: Default TTL in seconds
            hass: Optional Home Assistant instance for async file operations
        """
        self._cache_file = cache_file_path or PROPERTY_CACHE_FILE
        self._default_ttl = default_ttl
        self._hass = hass
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

        _LOGGER.debug("Initialized CachedData with TTL %s seconds", default_ttl)

    def _is_expired(self, cache_entry: dict[str, Any]) -> bool:
        """Check if a cache entry is expired.

        Args:
            cache_entry: Cache entry with 'timestamp' and 'ttl' fields

        Returns:
            True if expired, False otherwise
        """
        current_time = time.time()
        entry_time = cache_entry.get("timestamp", 0)
        ttl = cache_entry.get("ttl", self._default_ttl)

        return (current_time - entry_time) > ttl

    async def get(
        self, key: str, default: T | None = None, ttl: int | None = None
    ) -> T | None:
        """Get a value from cache.

        Args:
            key: Cache key
            default: Default value if not found or expired
            ttl: Optional TTL override

        Returns:
            Cached value or default
        """
        async with self._lock:
            if key not in self._cache:
                _LOGGER.debug("Cache miss for key: %s", key)
                return default

            cache_entry = self._cache[key]
            if self._is_expired(cache_entry):
                _LOGGER.debug("Cache expired for key: %s", key)
                del self._cache[key]
                return default

            _LOGGER.debug("Cache hit for key: %s", key)
            return cache_entry.get("data", default)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override (in seconds)
        """
        async with self._lock:
            cache_entry = {
                "data": value,
                "timestamp": time.time(),
                "ttl": ttl or self._default_ttl,
            }
            self._cache[key] = cache_entry
            _LOGGER.debug("Cached value for key: %s (TTL: %s)", key, cache_entry["ttl"])

        # Save to disk asynchronously
        await self._save_to_disk()

    async def delete(self, key: str) -> bool:
        """Delete a key from cache.

        Args:
            key: Cache key

        Returns:
            True if key existed, False otherwise
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                _LOGGER.debug("Deleted cache key: %s", key)
                await self._save_to_disk()
                return True
            return False

    async def clear(self) -> None:
        """Clear all cached data."""
        async with self._lock:
            self._cache.clear()
            _LOGGER.debug("Cleared all cache data")

        # Remove cache file
        await self._clear_disk_cache()

    async def cleanup_expired(self) -> int:
        """Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() if self._is_expired(entry)
            ]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                _LOGGER.debug("Cleaned up %s expired cache entries", len(expired_keys))
                await self._save_to_disk()

            return len(expired_keys)

    def _save_to_disk_sync(self) -> None:
        """Save cache to disk (synchronous helper)."""
        try:
            with open(self._cache_file, "w") as f:
                json.dump(self._cache, f, indent=2)

            # Set file permissions to be readable only by the owner
            os.chmod(self._cache_file, 0o600)
            _LOGGER.debug("Cache saved to disk: %s", self._cache_file)

        except Exception as e:
            _LOGGER.warning("Failed to save cache to disk: %s", e)

    async def _save_to_disk(self) -> None:
        """Save cache to disk."""
        try:
            if self._hass:
                # Use Home Assistant's executor for async file operations
                await self._hass.async_add_executor_job(self._save_to_disk_sync)
            else:
                # Fallback to synchronous operation
                self._save_to_disk_sync()
        except Exception as e:
            _LOGGER.warning("Failed to save cache to disk: %s", e)

    def _load_from_disk_sync(self) -> bool:
        """Load cache from disk (synchronous helper).

        Returns:
            True if loaded successfully, False otherwise
        """
        if not os.path.exists(self._cache_file):
            _LOGGER.debug("Cache file does not exist: %s", self._cache_file)
            return False

        try:
            with open(self._cache_file, "r") as f:
                cache_data = json.load(f)

            if not isinstance(cache_data, dict):
                _LOGGER.warning("Invalid cache file format")
                return False

            self._cache = cache_data
            _LOGGER.debug("Cache loaded from disk: %s entries", len(self._cache))
            return True

        except json.JSONDecodeError:
            _LOGGER.warning("Failed to parse cache file (invalid JSON)")
            return False
        except Exception as e:
            _LOGGER.warning("Failed to load cache from disk: %s", e)
            return False

    async def load_from_disk(self) -> bool:
        """Load cache from disk.

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            if self._hass:
                # Use Home Assistant's executor for async file operations
                return await self._hass.async_add_executor_job(
                    self._load_from_disk_sync
                )
            else:
                # Fallback to synchronous operation
                return self._load_from_disk_sync()
        except Exception as e:
            _LOGGER.warning("Failed to load cache from disk: %s", e)
            return False

    async def _clear_disk_cache(self) -> None:
        """Clear the disk cache file."""
        if os.path.exists(self._cache_file):
            try:
                if self._hass:
                    await self._hass.async_add_executor_job(os.remove, self._cache_file)
                else:
                    os.remove(self._cache_file)
                _LOGGER.debug("Cache file removed: %s", self._cache_file)
            except Exception as e:
                _LOGGER.warning("Failed to remove cache file: %s", e)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_entries = len(self._cache)
        expired_entries = sum(
            1 for entry in self._cache.values() if self._is_expired(entry)
        )

        return {
            "total_entries": total_entries,
            "expired_entries": expired_entries,
            "valid_entries": total_entries - expired_entries,
            "cache_file": self._cache_file,
            "default_ttl": self._default_ttl,
        }


class RetryWithBackoff:
    """Implements exponential backoff with jitter for retrying operations."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        backoff_multiplier: float = 2.0,
        max_jitter: float = 1.0,
    ):
        """Initialize retry handler.

        Args:
            max_retries: Maximum number of retries
            base_delay: Base delay in seconds
            backoff_multiplier: Multiplier for exponential backoff
            max_jitter: Maximum jitter to add in seconds
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.backoff_multiplier = backoff_multiplier
        self.max_jitter = max_jitter

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt with exponential backoff and jitter.

        Args:
            attempt: Current attempt number (0-based)

        Returns:
            Delay in seconds
        """
        # Exponential backoff
        delay = self.base_delay * (self.backoff_multiplier**attempt)

        # Add jitter to prevent thundering herd
        jitter = random.uniform(0, self.max_jitter)

        return delay + jitter

    async def retry(self, func, *args, **kwargs):
        """Retry a function with exponential backoff and jitter.

        Args:
            func: Async function to retry
            *args: Arguments to pass to function
            **kwargs: Keyword arguments to pass to function

        Returns:
            Result of the function

        Raises:
            The last exception encountered if all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if attempt < self.max_retries:
                    delay = self.calculate_delay(attempt)
                    _LOGGER.debug(
                        "Retry attempt %s/%s failed: %s. Retrying in %.2fs",
                        attempt + 1,
                        self.max_retries,
                        e,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    _LOGGER.error(
                        "All retry attempts failed after %s tries: %s",
                        self.max_retries + 1,
                        e,
                    )

        # Re-raise the last exception if all retries failed
        raise last_exception
