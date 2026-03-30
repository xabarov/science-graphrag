from science_graphrag.ingestion.dedup import (
    find_doi_in_text,
    normalize_doi,
    title_fingerprint,
)


def test_normalize_doi():
    assert normalize_doi("https://doi.org/10.1000/182") == "10.1000/182"
    assert normalize_doi("10.1000/182") == "10.1000/182"


def test_find_doi_in_text():
    t = "See https://doi.org/10.1145/3442188.3445922 for details."
    assert find_doi_in_text(t) == "10.1145/3442188.3445922"


def test_title_fingerprint_stable():
    assert title_fingerprint("Hello World", 2020) == title_fingerprint("Hello World", 2020)
    assert title_fingerprint("Hello World", 2020) != title_fingerprint("Hello World", 2021)
