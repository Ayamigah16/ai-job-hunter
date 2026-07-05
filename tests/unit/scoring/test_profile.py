from ai_job_hunter.scoring.profile import DEFAULT_SKILLS_PROFILE_PATH, load_scoring_profile


def test_loads_real_skills_profile():
    profile = load_scoring_profile(DEFAULT_SKILLS_PROFILE_PATH)
    assert "kubernetes" in profile.must_have_skills
    assert profile.weights["must_have_match"] > 0
