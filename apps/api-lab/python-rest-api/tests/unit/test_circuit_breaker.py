import pytest
from middleware.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError, CircuitState


class TestCircuitBreaker:
    @pytest.fixture
    def breaker(self):
        return CircuitBreaker(failure_threshold=3, recovery_timeout=1.0, name="test")

    async def test_initial_state_is_closed(self, breaker):
        assert breaker.state == CircuitState.CLOSED

    async def test_successful_call(self, breaker):
        async def success():
            return "ok"

        result = await breaker.call(success)
        assert result == "ok"
        assert breaker.state == CircuitState.CLOSED

    async def test_opens_after_threshold(self, breaker):
        async def fail():
            raise ConnectionError("fail")

        for _ in range(3):
            with pytest.raises(ConnectionError):
                await breaker.call(fail)

        assert breaker.state == CircuitState.OPEN

    async def test_open_rejects_calls(self, breaker):
        async def fail():
            raise ConnectionError("fail")

        for _ in range(3):
            with pytest.raises(ConnectionError):
                await breaker.call(fail)

        async def success():
            return "ok"

        with pytest.raises(CircuitBreakerOpenError):
            await breaker.call(success)

    async def test_success_resets_failures(self, breaker):
        async def fail():
            raise ConnectionError("fail")

        async def success():
            return "ok"

        # Two failures (below threshold)
        for _ in range(2):
            with pytest.raises(ConnectionError):
                await breaker.call(fail)

        # Success resets
        await breaker.call(success)
        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0
