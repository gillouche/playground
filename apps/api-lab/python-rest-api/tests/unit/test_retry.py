import pytest
from middleware.retry import with_retry


class TestWithRetry:
    async def test_succeeds_on_first_attempt(self):
        call_count = 0

        @with_retry(max_attempts=3, min_wait=0.01, max_wait=0.02)
        async def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await succeed()
        assert result == "ok"
        assert call_count == 1

    async def test_retries_on_connection_error_and_succeeds(self):
        call_count = 0

        @with_retry(max_attempts=3, min_wait=0.01, max_wait=0.02)
        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("connection lost")
            return "recovered"

        result = await flaky()
        assert result == "recovered"
        assert call_count == 2

    async def test_retries_on_timeout_error(self):
        call_count = 0

        @with_retry(max_attempts=3, min_wait=0.01, max_wait=0.02)
        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutError("timed out")
            return "done"

        result = await flaky()
        assert result == "done"
        assert call_count == 3

    async def test_retries_on_os_error(self):
        call_count = 0

        @with_retry(max_attempts=3, min_wait=0.01, max_wait=0.02)
        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OSError("os error")
            return "ok"

        result = await flaky()
        assert result == "ok"
        assert call_count == 2

    async def test_does_not_retry_on_value_error(self):
        call_count = 0

        @with_retry(max_attempts=3, min_wait=0.01, max_wait=0.02)
        async def bad():
            nonlocal call_count
            call_count += 1
            raise ValueError("not retryable")

        with pytest.raises(ValueError, match="not retryable"):
            await bad()
        assert call_count == 1

    async def test_raises_after_max_attempts_exhausted(self):
        call_count = 0

        @with_retry(max_attempts=3, min_wait=0.01, max_wait=0.02)
        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("still broken")

        with pytest.raises(ConnectionError, match="still broken"):
            await always_fail()
        assert call_count == 3

    async def test_works_with_sync_function(self):
        call_count = 0

        @with_retry(max_attempts=3, min_wait=0.01, max_wait=0.02)
        def sync_flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("fail")
            return "sync ok"

        result = sync_flaky()
        assert result == "sync ok"
        assert call_count == 2
