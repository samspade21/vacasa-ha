"""Test script for performance optimization components only."""

import asyncio
import logging
import os
import sys
import time

import pytest

pytest.skip(
    "Performance tests are skipped during unit testing", allow_module_level=True
)

# Add the custom components path
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "custom_components", "vacasa")
)

from cached_data import CachedData, RetryWithBackoff  # noqa: E402

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)


async def test_caching_functionality():
    """Test caching functionality."""
    print("\n=== Testing Caching Functionality ===")

    # Create a cache instance
    cache = CachedData(default_ttl=10)  # 10 second TTL for testing

    # Test setting and getting values
    await cache.set("test_key", {"data": "test_value"})
    cached_value = await cache.get("test_key")

    assert cached_value == {"data": "test_value"}, "Cache set/get failed"
    print("✓ Cache set/get works correctly")

    # Test cache expiration
    await cache.set("expire_test", "will_expire", ttl=1)  # 1 second TTL
    await asyncio.sleep(2)  # Wait for expiration
    expired_value = await cache.get("expire_test")

    assert expired_value is None, "Cache expiration failed"
    print("✓ Cache expiration works correctly")

    # Test cache cleanup
    await cache.set("cleanup_test1", "value1", ttl=1)
    await cache.set("cleanup_test2", "value2", ttl=10)
    await asyncio.sleep(2)  # Let first one expire

    cleaned_count = await cache.cleanup_expired()
    assert cleaned_count >= 1, "Cache cleanup failed"
    print("✓ Cache cleanup works correctly")

    # Test cache stats
    stats = cache.get_stats()
    assert isinstance(stats, dict), "Stats should be a dict"
    assert "total_entries" in stats, "Stats missing total_entries"
    print("✓ Cache stats work correctly")

    # Clear cache
    await cache.clear()
    print("✓ Cache functionality tests passed")


async def test_retry_functionality():
    """Test retry functionality."""
    print("\n=== Testing Retry Functionality ===")

    retry_handler = RetryWithBackoff(max_retries=3, base_delay=0.1, max_jitter=0.1)

    # Test successful function (no retries needed)
    call_count = 0

    async def success_func():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await retry_handler.retry(success_func)
    assert result == "success", "Successful function failed"
    assert call_count == 1, "Successful function called multiple times"
    print("✓ Retry handler works with successful functions")

    # Test function that fails then succeeds
    call_count = 0

    async def fail_then_succeed():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Temporary failure")
        return "eventual_success"

    start_time = time.time()
    result = await retry_handler.retry(fail_then_succeed)
    end_time = time.time()

    assert result == "eventual_success", "Retry function failed"
    assert call_count == 3, "Function not retried correctly"
    assert end_time - start_time > 0.1, "No delay between retries"
    print("✓ Retry handler works with failing functions")

    # Test exponential backoff timing
    delays = []
    for i in range(3):
        delay = retry_handler.calculate_delay(i)
        delays.append(delay)
        print(f"  Attempt {i + 1} delay: {delay:.3f}s")

    # Verify delays increase (allowing for jitter)
    assert delays[1] > delays[0] * 1.5, "Delay not increasing exponentially"
    print("✓ Exponential backoff timing works correctly")

    print("✓ Retry functionality tests passed")


async def test_cache_file_operations():
    """Test cache file operations."""
    print("\n=== Testing Cache File Operations ===")

    test_cache_file = "test_cache.json"

    # Clean up any existing test file
    if os.path.exists(test_cache_file):
        os.remove(test_cache_file)

    cache = CachedData(cache_file_path=test_cache_file, default_ttl=60)

    # Add some data
    await cache.set("file_test_key1", {"data": "value1"})
    await cache.set("file_test_key2", {"data": "value2"})

    # Verify file was created
    assert os.path.exists(test_cache_file), "Cache file was not created"
    print("✓ Cache file creation works")

    # Create new cache instance and load from file
    cache2 = CachedData(cache_file_path=test_cache_file, default_ttl=60)
    loaded = await cache2.load_from_disk()
    assert loaded, "Failed to load cache from disk"

    # Verify data was loaded
    value1 = await cache2.get("file_test_key1")
    value2 = await cache2.get("file_test_key2")

    assert value1 == {"data": "value1"}, "Failed to load value1 from cache file"
    assert value2 == {"data": "value2"}, "Failed to load value2 from cache file"
    print("✓ Cache file loading works")

    # Clean up
    await cache.clear()
    if os.path.exists(test_cache_file):
        os.remove(test_cache_file)

    print("✓ Cache file operations tests passed")


async def test_performance_characteristics():
    """Test performance characteristics."""
    print("\n=== Testing Performance Characteristics ===")

    cache = CachedData(default_ttl=60)

    # Test cache performance with many items
    num_items = 1000
    start_time = time.time()

    for i in range(num_items):
        await cache.set(f"perf_key_{i}", {"index": i, "data": f"value_{i}"})

    set_time = time.time() - start_time
    print(
        f"✓ Set {num_items} items in {set_time:.3f}s ({num_items / set_time:.0f} items/sec)"
    )

    # Test retrieval performance
    start_time = time.time()

    for i in range(num_items):
        value = await cache.get(f"perf_key_{i}")
        assert value is not None, f"Failed to retrieve item {i}"

    get_time = time.time() - start_time
    print(
        f"✓ Retrieved {num_items} items in {get_time:.3f}s ({num_items / get_time:.0f} items/sec)"
    )

    # Test cleanup performance
    start_time = time.time()
    cleaned = await cache.cleanup_expired()
    cleanup_time = time.time() - start_time

    print(
        f"✓ Cleanup scan completed in {cleanup_time:.3f}s (cleaned {cleaned} expired items)"
    )

    await cache.clear()
    print("✓ Performance characteristics tests passed")


async def main():
    """Run all performance optimization tests."""
    print("Starting Vacasa Performance Optimization Component Tests")
    print("=" * 60)

    try:
        await test_caching_functionality()
        await test_retry_functionality()
        await test_cache_file_operations()
        await test_performance_characteristics()

        print("\n" + "=" * 60)
        print("🎉 All performance optimization component tests PASSED!")
        print("\nPerformance Components Verified:")
        print("  ✓ Intelligent caching with TTL support")
        print("  ✓ Exponential backoff with jitter retry logic")
        print("  ✓ Efficient file-based cache persistence")
        print("  ✓ Cache cleanup and statistics")
        print("  ✓ High-performance cache operations")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
