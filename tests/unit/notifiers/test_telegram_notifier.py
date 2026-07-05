import pytest
import requests
import responses

from ai_job_hunter.notifiers.telegram_notifier import TelegramNotifier


def make_notifier() -> TelegramNotifier:
    return TelegramNotifier(bot_token="TESTTOKEN", chat_id="12345")


@responses.activate
def test_notify_posts_summary_message(make_scored_job):
    responses.add(
        responses.POST,
        "https://api.telegram.org/botTESTTOKEN/sendMessage",
        json={"ok": True},
        status=200,
    )
    jobs = [make_scored_job(score=90.0, company="Acme", title="Platform Engineer")]

    make_notifier().notify(jobs)

    assert len(responses.calls) == 1
    body = responses.calls[0].request.body
    body_text = body.decode() if isinstance(body, bytes) else body
    assert "12345" in body_text
    assert "Acme" in body_text


@responses.activate
def test_notify_does_nothing_for_empty_job_list():
    make_notifier().notify([])
    assert len(responses.calls) == 0


@responses.activate
def test_notify_raises_on_http_error(make_scored_job):
    responses.add(
        responses.POST,
        "https://api.telegram.org/botTESTTOKEN/sendMessage",
        json={"ok": False, "description": "bad request"},
        status=400,
    )
    jobs = [make_scored_job(score=90.0)]

    with pytest.raises(requests.exceptions.HTTPError):
        make_notifier().notify(jobs)
