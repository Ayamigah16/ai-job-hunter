from ai_job_hunter.notifiers.dispatcher import NotifierDispatcher


class _RecordingNotifier:
    def __init__(self):
        self.calls: list = []

    def notify(self, new_jobs):
        self.calls.append(new_jobs)


class _FailingNotifier:
    def notify(self, new_jobs):
        raise RuntimeError("simulated notifier failure")


def test_dispatcher_fans_out_to_all_notifiers(make_scored_job):
    jobs = [make_scored_job()]
    first = _RecordingNotifier()
    second = _RecordingNotifier()

    NotifierDispatcher([first, second]).notify(jobs)

    assert first.calls == [jobs]
    assert second.calls == [jobs]


def test_one_notifier_failing_does_not_block_the_others(make_scored_job):
    jobs = [make_scored_job()]
    healthy = _RecordingNotifier()

    NotifierDispatcher([_FailingNotifier(), healthy]).notify(jobs)

    assert healthy.calls == [jobs]


def test_dispatcher_does_nothing_for_empty_job_list():
    recorder = _RecordingNotifier()
    NotifierDispatcher([recorder]).notify([])
    assert recorder.calls == []
