"""Tests for the cached data utilities used by the Vacasa integration."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.vacasa.cached_data import CachedData, RetryWithBackoff


@pytest.mark.asyncio
async def test_set_and_get_cached_value(tmp_path: Path) -> None:
    """Values written to the cache should be retrievable and persisted to disk."""

    cache_file = tmp_path / "cache.json"
    cached_data = CachedData(cache_file_path=str(cache_file), default_ttl=60)

    await cached_data.set("answer", {"value": 42})
    result = await cached_data.get("answer")

    assert result == {"value": 42}
    assert cache_file.exists()

    with cache_file.open() as fh:
        disk_cache = json.load(fh)

    assert "answer" in disk_cache
    assert disk_cache["answer"]["data"] == {"value": 42}


@pytest.mark.asyncio
async def test_get_expired_entry_returns_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Expired entries should be treated as a cache miss and removed."""

    cache_file = tmp_path / "cache.json"
    cached_data = CachedData(cache_file_path=str(cache_file), default_ttl=10)

    monkeypatch.setattr("custom_components.vacasa.cached_data.time.time", lambda: 100.0)
    await cached_data.set("ephemeral", "value", ttl=5)

    monkeypatch.setattr("custom_components.vacasa.cached_data.time.time", lambda: 200.0)
    result = await cached_data.get("ephemeral", default="missing")

    assert result == "missing"
    assert "ephemeral" not in cached_data._cache


@pytest.mark.asyncio
async def test_cleanup_expired_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Only expired entries should be removed during cleanup."""

    cache_file = tmp_path / "cache.json"
    cached_data = CachedData(cache_file_path=str(cache_file), default_ttl=50)

    monkeypatch.setattr("custom_components.vacasa.cached_data.time.time", lambda: 100.0)
    await cached_data.set("fresh", 1, ttl=200)
    await cached_data.set("old", 2, ttl=10)

    monkeypatch.setattr("custom_components.vacasa.cached_data.time.time", lambda: 400.0)
    removed = await cached_data.cleanup_expired()

    assert removed == 1
    assert "fresh" in cached_data._cache
    assert "old" not in cached_data._cache


@pytest.mark.asyncio
async def test_clear_removes_cache_file(tmp_path: Path) -> None:
    """Clearing the cache should empty in-memory data and delete the cache file."""

    cache_file = tmp_path / "cache.json"
    cached_data = CachedData(cache_file_path=str(cache_file))

    await cached_data.set("answer", 42)
    assert cache_file.exists()

    await cached_data.clear()

    assert not cache_file.exists()
    assert cached_data._cache == {}


@pytest.mark.asyncio
async def test_delete_handles_missing_key(tmp_path: Path) -> None:
    """Deleting an unknown key should return False and leave the cache untouched."""

    cache_file = tmp_path / "cache.json"
    cached_data = CachedData(cache_file_path=str(cache_file))

    result = await cached_data.delete("ghost")

    assert result is False
    assert cached_data._cache == {}


@pytest.mark.asyncio
async def test_delete_existing_key(tmp_path: Path) -> None:
    """Deleting an existing key should return True and persist changes."""

    cache_file = tmp_path / "cache.json"
    cached_data = CachedData(cache_file_path=str(cache_file))

    await cached_data.set("present", "value")
    assert "present" in cached_data._cache

    result = await cached_data.delete("present")

    assert result is True
    assert "present" not in cached_data._cache

    with cache_file.open() as fh:
        disk_cache = json.load(fh)

    assert disk_cache == {}


@pytest.mark.asyncio
async def test_load_from_disk_invalid_json(tmp_path: Path) -> None:
    """Invalid JSON on disk should be handled gracefully."""

    cache_file = tmp_path / "cache.json"
    cache_file.write_text("{invalid json")

    cached_data = CachedData(cache_file_path=str(cache_file))

    loaded = await cached_data.load_from_disk()

    assert loaded is False
    assert cached_data._cache == {}


@pytest.mark.asyncio
async def test_load_from_disk_valid_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Valid cache data on disk should be loaded into memory."""

    cache_file = tmp_path / "cache.json"
    cache_contents = {
        "answer": {"data": 42, "timestamp": 100.0, "ttl": 500.0},
    }
    cache_file.write_text(json.dumps(cache_contents))

    cached_data = CachedData(cache_file_path=str(cache_file))

    monkeypatch.setattr("custom_components.vacasa.cached_data.time.time", lambda: 200.0)
    loaded = await cached_data.load_from_disk()

    assert loaded is True
    assert await cached_data.get("answer") == 42


@pytest.mark.asyncio
async def test_run_io_task_uses_hass_executor(tmp_path: Path) -> None:
    """When a hass instance is available the executor should be used for IO tasks."""

    hass = SimpleNamespace(async_add_executor_job=AsyncMock())
    hass.async_add_executor_job.return_value = "executed"

    cached_data = CachedData(cache_file_path=str(tmp_path / "cache.json"), hass=hass)

    result = await cached_data._run_io_task(lambda: "executed")

    assert result == "executed"
    hass.async_add_executor_job.assert_awaited_once()


def test_calculate_delay_with_jitter(monkeypatch: pytest.MonkeyPatch) -> None:
    """The backoff delay should include jitter from the RNG."""

    retry = RetryWithBackoff(base_delay=1.0, backoff_multiplier=2.0, max_jitter=1.0)
    monkeypatch.setattr(
        "custom_components.vacasa.cached_data.random.uniform", lambda _a, _b: 0.5
    )

    assert retry.calculate_delay(2) == pytest.approx(4.5)


@pytest.mark.asyncio
async def test_retry_with_backoff_eventually_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Retry logic should sleep between attempts and return the eventual value."""

    retry = RetryWithBackoff(max_retries=2, base_delay=1.0, backoff_multiplier=2.0, max_jitter=0.0)
    sleep_calls: list[float] = []

    async def fake_sleep(delay: float) -> None:  # pragma: no cover - defined for clarity
        sleep_calls.append(delay)

    monkeypatch.setattr("custom_components.vacasa.cached_data.asyncio.sleep", fake_sleep)

    attempts = {"count": 0}

    async def flaky() -> str:
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise RuntimeError("fail once")
        return "success"

    result = await retry.retry(flaky)

    assert result == "success"
    assert sleep_calls == [1.0]


@pytest.mark.asyncio
async def test_retry_with_backoff_raises_after_exhaustion(monkeypatch: pytest.MonkeyPatch) -> None:
    """After the allowed attempts the last error should be propagated."""

    retry = RetryWithBackoff(max_retries=1, base_delay=0.1, backoff_multiplier=2.0, max_jitter=0.0)

    async def fake_sleep(_delay: float) -> None:  # pragma: no cover - defined for clarity
        return None

    monkeypatch.setattr("custom_components.vacasa.cached_data.asyncio.sleep", fake_sleep)

    async def always_fail() -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError):
        await retry.retry(always_fail)

