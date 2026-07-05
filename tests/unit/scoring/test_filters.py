from ai_job_hunter.scoring.filters import (
    africa_friendly_hint,
    is_relevant,
    is_remote_friendly,
    matched_must_have_skills,
    matches_role_title,
    sponsorship_mentioned,
)
from ai_job_hunter.scoring.profile import ScoringProfile


def make_profile(**overrides) -> ScoringProfile:
    defaults = dict(
        role_title_keywords=["platform engineer", "devops engineer", "site reliability"],
        must_have_skills=["kubernetes", "docker"],
        nice_to_have_skills=["terraform"],
        sponsorship_keywords=["visa sponsorship"],
        remote_positive_keywords=["fully distributed"],
        africa_friendly_positive_keywords=["remote - global"],
        africa_friendly_negative_keywords=["us only"],
        weights={"must_have_match": 10, "role_title_match": 15},
    )
    defaults.update(overrides)
    return ScoringProfile.model_validate(defaults)


def test_matches_role_title(make_job):
    profile = make_profile()
    assert matches_role_title(make_job(title="Senior Platform Engineer"), profile)
    assert not matches_role_title(make_job(title="Account Executive"), profile)


def test_matched_must_have_skills(make_job):
    profile = make_profile()
    job = make_job(description_raw="You will manage our Kubernetes and Docker fleet.")
    assert set(matched_must_have_skills(job, profile)) == {"kubernetes", "docker"}


def test_is_relevant_excludes_unrelated_jobs(make_job):
    profile = make_profile()
    unrelated = make_job(title="Account Executive", description_raw="Sell things to people.")
    assert not is_relevant(unrelated, profile)

    by_title = make_job(title="Site Reliability Engineer", description_raw="")
    assert is_relevant(by_title, profile)

    by_skill = make_job(title="Infra Wizard", description_raw="Deep Kubernetes expertise needed.")
    assert is_relevant(by_skill, profile)


def test_is_remote_friendly(make_job):
    profile = make_profile()
    assert is_remote_friendly(make_job(remote=True), profile)
    onsite = make_job(remote=False, description_raw="", location_raw="NYC")
    assert not is_remote_friendly(onsite, profile)
    fallback = make_job(remote=None, description_raw="We are a fully distributed team.")
    assert is_remote_friendly(fallback, profile)


def test_sponsorship_mentioned(make_job):
    profile = make_profile()
    job = make_job(description_raw="We offer visa sponsorship for this role.")
    assert sponsorship_mentioned(job, profile)
    assert not sponsorship_mentioned(make_job(description_raw="No sponsorship mentioned."), profile)


def test_africa_friendly_hint(make_job):
    profile = make_profile()
    likely = make_job(description_raw="Remote - Global")
    unlikely = make_job(description_raw="US Only applicants")
    unknown = make_job(description_raw="no hint here")
    assert africa_friendly_hint(likely, profile) == "likely"
    assert africa_friendly_hint(unlikely, profile) == "unlikely"
    assert africa_friendly_hint(unknown, profile) == "unknown"
