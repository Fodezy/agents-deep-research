"""Simple test to verify async pytest setup works."""

import asyncio
import pytest

async def test_simple_async():
    """Test that async tests work."""
    await asyncio.sleep(0.1)
    assert True

def test_simple_sync():
    """Test that sync tests still work."""
    assert True