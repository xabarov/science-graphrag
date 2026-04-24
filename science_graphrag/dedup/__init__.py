"""Wave L dedup: embedding similarity + LLM judge + Postgres review queue."""

from science_graphrag.dedup.fingerprints import author_pair_fingerprint, work_pair_fingerprint

__all__ = ["author_pair_fingerprint", "work_pair_fingerprint"]
