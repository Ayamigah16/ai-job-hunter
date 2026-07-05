from ai_job_hunter.regions import lookup_location


def test_lookup_known_country():
    country, region = lookup_location("Berlin, Germany")
    assert country == "Germany"
    assert region == "Europe"


def test_lookup_generic_remote_has_no_country_label():
    country, region = lookup_location("Remote - Worldwide")
    assert country == ""
    assert region == "Global Remote"


def test_lookup_unknown_location():
    country, region = lookup_location("Somewhere unlisted")
    assert country == ""
    assert region == "Unknown"
