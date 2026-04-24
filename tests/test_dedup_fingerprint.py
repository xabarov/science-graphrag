from science_graphrag.dedup.fingerprints import author_pair_fingerprint, work_pair_fingerprint


def test_work_pair_fingerprint_stable() -> None:
    fp1 = work_pair_fingerprint("ws1", "b", "a")
    fp2 = work_pair_fingerprint("ws1", "a", "b")
    assert fp1 == fp2
    assert len(fp1) == 64


def test_work_pair_fingerprint_diff_workspace() -> None:
    assert work_pair_fingerprint("ws1", "a", "b") != work_pair_fingerprint("ws2", "a", "b")


def test_author_pair_fingerprint() -> None:
    assert author_pair_fingerprint("w", "x", "y") == author_pair_fingerprint("w", "y", "x")
