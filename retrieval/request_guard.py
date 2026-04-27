import logging
import random
import time
from typing import Callable, TypeVar

import httpx


T = TypeVar("T")

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_RETRYABLE_ERROR_MARKERS = (
    "RESOURCE_EXHAUSTED",
    "Too Many Requests",
    "ReadError",
    "timed out",
    "Service Unavailable",
)


class RequestGuard:
    """Serialises and retries remote AI requests that can fail transiently."""

    def __init__(
        self,
        logger: logging.Logger,
        min_interval_seconds: float = 1.0,
        max_retries: int = 3,
        base_delay_seconds: float = 60.0,
        max_delay_seconds: float = 300.0,
    ):
        self._logger = logger
        self._min_interval_seconds = min_interval_seconds
        self._max_retries = max_retries
        self._base_delay_seconds = base_delay_seconds
        self._max_delay_seconds = max_delay_seconds
        self._next_allowed_at = 0.0

    def setup(self) -> None:
        """Reset internal pacing state before a run starts."""
        self._next_allowed_at = 0.0
        self._logger.info(
            "RequestGuard setup complete (min_interval=%.1fs, max_retries=%d).",
            self._min_interval_seconds,
            self._max_retries,
        )

    def _wait_for_slot(self) -> None:
        """Apply a small gap between external requests to smooth bursts."""
        delay_seconds = self._next_allowed_at - time.monotonic()
        if delay_seconds > 0:
            time.sleep(delay_seconds)

    @staticmethod
    def _status_code(error: Exception) -> int | None:
        """Extract HTTP-like status code from known exception shapes."""
        status_code = getattr(error, "status_code", None)
        if isinstance(status_code, int):
            return status_code
        return None

    def _is_retryable(self, error: Exception) -> bool:
        """Return whether a failure looks like a transient remote issue."""
        if isinstance(error, (httpx.ReadError, httpx.TimeoutException, httpx.ConnectError)):
            return True

        status_code = self._status_code(error)
        if status_code in _RETRYABLE_STATUS_CODES:
            return True

        error_text = str(error)
        return any(marker in error_text for marker in _RETRYABLE_ERROR_MARKERS)

    def _backoff_seconds(self, attempt: int) -> float:
        """Compute exponential backoff with a small jitter."""
        capped_delay = min(self._base_delay_seconds * (2 ** (attempt - 1)), self._max_delay_seconds)
        return capped_delay + random.uniform(0.0, 1.0)

    def run(self, operation_name: str, operation: Callable[[], T]) -> T:
        """Run a remote operation with pacing and transient-error retries."""
        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            self._wait_for_slot()
            try:
                result = operation()
                self._next_allowed_at = time.monotonic() + self._min_interval_seconds
                return result
            except Exception as error:
                last_error = error
                if not self._is_retryable(error) or attempt == self._max_retries:
                    raise

                delay_seconds = self._backoff_seconds(attempt)
                self._logger.warning(
                    "Transient remote failure during %s (attempt %d/%d, status=%s). Retrying in %.1f seconds.",
                    operation_name,
                    attempt,
                    self._max_retries,
                    self._status_code(error) or "n/a",
                    delay_seconds,
                )
                time.sleep(delay_seconds)

        raise last_error
