import logging

from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger("api-lab.retry")


def _log_retry(retry_state: RetryCallState):
    logger.warning(
        f"Retrying {retry_state.fn.__name__} "
        f"(attempt {retry_state.attempt_number}): {retry_state.outcome.exception()}"
    )


def with_retry(max_attempts: int = 3, min_wait: float = 0.5, max_wait: float = 5.0):
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        before_sleep=_log_retry,
        reraise=True,
    )
