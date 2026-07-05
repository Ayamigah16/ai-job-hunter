"""Sends one summary email for newly-appended high-scoring jobs, via SMTP."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import TYPE_CHECKING

from ai_job_hunter.notifiers.base import format_job_summary

if TYPE_CHECKING:
    from ai_job_hunter.models import ScoredJob


class EmailNotifier:
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addr: str,
    ) -> None:
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._username = username
        self._password = password
        self._from_addr = from_addr
        self._to_addr = to_addr

    def notify(self, new_jobs: list[ScoredJob]) -> None:
        if not new_jobs:
            return

        message = EmailMessage()
        message["Subject"] = f"AI Job Hunter: {len(new_jobs)} new high-match role(s)"
        message["From"] = self._from_addr
        message["To"] = self._to_addr
        message.set_content(format_job_summary(new_jobs))

        with smtplib.SMTP(self._smtp_host, self._smtp_port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(self._username, self._password)
            smtp.send_message(message)
