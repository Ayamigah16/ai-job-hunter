from ai_job_hunter.scoring.profile import ScoringProfile
from ai_job_hunter.scoring.scorer import score_job


def make_profile() -> ScoringProfile:
    return ScoringProfile.model_validate(
        {
            "role_title_keywords": ["platform engineer"],
            "must_have_skills": ["kubernetes", "docker"],
            "nice_to_have_skills": ["terraform"],
            "sponsorship_keywords": ["visa sponsorship"],
            "remote_positive_keywords": [],
            "africa_friendly_positive_keywords": [],
            "africa_friendly_negative_keywords": [],
            "weights": {
                "must_have_match": 10,
                "nice_to_have_match": 3,
                "role_title_match": 15,
                "remote_positive": 10,
                "salary_disclosed": 5,
                "sponsorship_mentioned": 5,
            },
        }
    )


def test_score_job_full_match(make_job):
    profile = make_profile()
    job = make_job(
        title="Senior Platform Engineer",
        description_raw="Kubernetes, Docker, Terraform. We offer visa sponsorship.",
        remote=True,
        salary_min=90000,
        salary_max=130000,
    )
    result = score_job(job, profile)
    # 2*10 (must-have) + 1*3 (nice-to-have) + 15 (title) + 10 (remote) + 5 (salary) + 5 (sponsor)
    assert result.total_score == 58
    assert set(result.matched_must_have) == {"kubernetes", "docker"}
    assert result.matched_nice_to_have == ["terraform"]
    assert result.sponsorship_mentioned is True
    assert result.salary_disclosed is True


def test_score_job_no_match_scores_zero(make_job):
    profile = make_profile()
    job = make_job(title="Account Executive", description_raw="Sales quota.", remote=False)
    result = score_job(job, profile)
    assert result.total_score == 0
    assert result.matched_must_have == []


def test_higher_relevance_scores_higher(make_job):
    profile = make_profile()
    weak = make_job(title="Infra Helper", description_raw="Kubernetes basics.", remote=False)
    strong = make_job(
        title="Senior Platform Engineer",
        description_raw="Kubernetes, Docker, Terraform.",
        remote=True,
    )
    assert score_job(strong, profile).total_score > score_job(weak, profile).total_score
