"""Async retry with exponential backoff.

Ported from ``pymigrate/migrate-worker/app/core/retry.py`` (``time.sleep`` ->
``asyncio.sleep``). Retries on any ``Exception``; re-raises the last one after
``tries`` attempts.
"""

import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


async def retry(
    fn: Callable[[], Awaitable[T]],
    *,
    tries: int = 3,
    base_delay: float = 4.0,
) -> T:
    delay = base_delay
    for attempt in range(1, tries + 1):
        try:
            return await fn()
        except Exception as e:
            if attempt >= tries:
                logger.error('attempt %d/%d failed, giving up: %s', attempt, tries, e)
                raise
            logger.warning(
                'attempt %d/%d failed (%s), retrying in %.1fs', attempt, tries, e, delay
            )
            await asyncio.sleep(delay)
            delay *= 2
    raise AssertionError('unreachable')
