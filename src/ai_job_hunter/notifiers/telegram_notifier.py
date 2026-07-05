"""Sends one summary Telegram message for newly-appended high-scoring jobs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import requests

from ai_job_hunter.notifiers.base import format_job_summary

if TYPE_CHECKING:
    from ai_job_hunter.models import ScoredJob

# Telegram truncates/rejects messages over 4096 UTF-16 code units.
_TELEGRAM_MESSAGE_LIMIT = 4000


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id

    def notify(self, new_jobs: list[ScoredJob]) -> None:
        if not new_jobs:
            return

        text = format_job_summary(new_jobs)[:_TELEGRAM_MESSAGE_LIMIT]
        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        response = requests.post(
            url,
            json={"chat_id": self._chat_id, "text": text, "disable_web_page_preview": True},
            timeout=15,
        )
        response.raise_for_status()
