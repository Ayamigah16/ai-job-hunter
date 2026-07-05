"""Fans out to every configured notifier; one channel's failure never blocks another."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_job_hunter.models import ScoredJob
    from ai_job_hunter.notifiers.base import Notifier

logger = logging.getLogger(__name__)


class NotifierDispatcher:
    def __init__(self, notifiers: list[Notifier]) -> None:
        self._notifiers = notifiers

    def notify(self, new_jobs: list[ScoredJob]) -> None:
        if not new_jobs:
            return
        for notifier in self._notifiers:
            try:
                notifier.notify(new_jobs)
            except Exception:
                logger.warning(
                    "Notifier %s failed to send", type(notifier).__name__, exc_info=True
                )
