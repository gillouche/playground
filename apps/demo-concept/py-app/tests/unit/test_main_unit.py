import pytest
from main import healthz, ready, root

@pytest.mark.asyncio
async def test_healthz():
    res = await healthz()
    assert res == {"status": "ok"}

@pytest.mark.asyncio
async def test_ready():
    res = await ready()
    assert res == {"status": "ready"}

@pytest.mark.asyncio
async def test_root():
    # Test valid name
    res = await root("Alice")
    assert res == {"message": "Hello, Alice! Welcome to the Playground (unknown)."}
    
    # Test default
    res = await root(None)
    assert res == {"message": "Hello, World! Welcome to the Playground (unknown)."}
