from ai_job_hunter.dedup import compute_job_id, dedup_jobs


def test_compute_job_id_stable_for_same_url():
    id_a = compute_job_id("Acme", "Platform Engineer", "https://acme.com/jobs/1?utm_source=x")
    id_b = compute_job_id("Acme", "Platform Engineer", "https://acme.com/jobs/1")
    assert id_a == id_b


def test_compute_job_id_ignores_trailing_slash_and_case():
    id_a = compute_job_id("Acme", "Platform Engineer", "https://Acme.com/jobs/1/")
    id_b = compute_job_id("Acme", "Platform Engineer", "https://acme.com/jobs/1")
    assert id_a == id_b


def test_compute_job_id_differs_for_different_urls():
    id_a = compute_job_id("Acme", "Platform Engineer", "https://acme.com/jobs/1")
    id_b = compute_job_id("Acme", "Platform Engineer", "https://acme.com/jobs/2")
    assert id_a != id_b


def test_compute_job_id_falls_back_to_company_title_when_no_url():
    id_a = compute_job_id("Acme", "Platform Engineer", None)
    id_b = compute_job_id("acme", "  platform   engineer  ", None)
    assert id_a == id_b


def test_dedup_jobs_collapses_same_posting_from_two_sources(make_job):
    company_board_posting = make_job(
        company="Acme",
        title="Platform Engineer",
        url="https://boards.greenhouse.io/acme/jobs/1",
        source_ats="greenhouse",
    )
    aggregator_posting = make_job(
        company="Acme",
        title="Platform Engineer",
        url="https://boards.greenhouse.io/acme/jobs/1?utm_source=remoteok",
        source_ats="remoteok",
    )
    distinct_posting = make_job(
        company="Acme",
        title="Data Engineer",
        url="https://boards.greenhouse.io/acme/jobs/2",
    )

    deduped = dedup_jobs([company_board_posting, aggregator_posting, distinct_posting])

    assert len(deduped) == 2
    assert deduped[0] is company_board_posting
    assert deduped[1] is distinct_posting
