from unittest.mock import MagicMock, patch

from ai_job_hunter.notifiers.email_notifier import EmailNotifier


def make_notifier() -> EmailNotifier:
    return EmailNotifier(
        smtp_host="smtp.example.com",
        smtp_port=587,
        username="bot@example.com",
        password="secret",
        from_addr="bot@example.com",
        to_addr="me@example.com",
    )


def test_notify_sends_one_email_with_all_jobs(make_scored_job):
    jobs = [
        make_scored_job(score=90.0, company="Acme", title="Platform Engineer"),
        make_scored_job(score=80.0, company="Globex", title="SRE"),
    ]

    with patch("ai_job_hunter.notifiers.email_notifier.smtplib.SMTP") as smtp_cls:
        smtp_instance = MagicMock()
        smtp_cls.return_value.__enter__.return_value = smtp_instance

        make_notifier().notify(jobs)

        smtp_instance.starttls.assert_called_once()
        smtp_instance.login.assert_called_once_with("bot@example.com", "secret")
        smtp_instance.send_message.assert_called_once()

        sent_message = smtp_instance.send_message.call_args[0][0]
        assert "2 new high-match role(s)" in sent_message["Subject"]
        body = sent_message.get_content()
        assert "Acme" in body
        assert "Globex" in body


def test_notify_does_nothing_for_empty_job_list():
    with patch("ai_job_hunter.notifiers.email_notifier.smtplib.SMTP") as smtp_cls:
        make_notifier().notify([])
        smtp_cls.assert_not_called()
