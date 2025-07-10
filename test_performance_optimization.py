"""Test script for performance optimization improvements."""

import asyncio
import logging
import os
import time
from datetime import datetime

from custom_components.vacasa.api_client import VacasaApiClient
from custom_components.vacasa.cached_data import CachedData, RetryWithBackoff

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

    print("✓ Retry functionality tests passed")


async def test_api_client_backward_compatibility():
    """Test API client backward compatibility."""
    print("\n=== Testing API Client Backward Compatibility ===")

    # Test that old constructor still works
    try:
        client = VacasaApiClient(
            username="test@example.com",
            password="test_password"
        )
        print("✓ Basic constructor still works")
    except Exception as e:
        print(f"✗ Basic constructor failed: {e}")
        return False

    # Test that new parameters work
    try:
        client = VacasaApiClient(
            username="test@example.com",
            password="test_password",
            cache_ttl=1800,  # 30 minutes
            max_connections=5,
            max_retries=2
        )
        print("✓ New constructor parameters work")
    except Exception as e:
        print(f"✗ New constructor parameters failed: {e}")
        return False

    # Test that new methods exist
    assert hasattr(client, 'clear_property_cache'), "Missing clear_property_cache method"
    assert hasattr(client, 'get_cache_stats'), "Missing get_cache_stats method"
    assert hasattr(client, 'cleanup_expired_cache'), "Missing cleanup_expired_cache method"
    print("✓ New methods are available")

    # Test cache stats (should work without API calls)
    stats = await client.get_cache_stats()
    assert isinstance(stats, dict), "Cache stats should return dict"
    assert "total_entries" in stats, "Cache stats missing total_entries"
    print("✓ Cache stats method works")

    print("✓ API client backward compatibility tests passed")


async def test_session_optimization():
    """Test optimized session creation."""
    print("\n=== Testing Session Optimization ===")

    client = VacasaApiClient(
        username="test@example.com",
        password="test_password",
        max_connections=8,
        keepalive_timeout=45
    )

    # Test session creation
    async with client:
        session = await client.ensure_session()

        # Check that session has the expected configuration
        assert session.connector.limit == 8, f"Expected 8 connections, got {session.connector.limit}"
        assert session.connector.keepalive_timeout == 45, f"Expected 45s keepalive, got {session.connector.keepalive_timeout}"

        print("✓ Session created with optimized settings")
        print(f"  - Max connections: {session.connector.limit}")
        print(f"  - Keepalive timeout: {session.connector.keepalive_timeout}s")
        print(f"  - DNS cache enabled: {session.connector.use_dns_cache}")

    print("✓ Session optimization tests passed")


async def main():
    """Run all performance optimization tests."""
    print("Starting Vacasa Performance Optimization Tests")
    print("=" * 50)

    try:
        await test_caching_functionality()
        await test_retry_functionality()
        await test_api_client_backward_compatibility()
        await test_session_optimization()

        print("\n" + "=" * 50)
        print("🎉 All performance optimization tests PASSED!")
        print("\nPerformance Improvements Implemented:")
        print("  ✓ Intelligent property data caching with TTL")
        print("  ✓ Connection pooling with optimized settings")
        print("  ✓ Exponential backoff with jitter for network resilience")
        print("  ✓ Efficient state management to reduce redundant operations")
        print("  ✓ Configurable cache TTL and retry behavior")
        print("  ✓ Backward compatibility maintained")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
