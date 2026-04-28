"""Shared string constants for reader graph projection (work + workspace alignment)."""

# Prefix for deterministic surrogate Author ids when OF_AUTHOR is absent from payload.
READER_SYNTHETIC_AUTHOR_ID_PREFIX = "va:"

# Salt segment for SHA-256 input when synthesizing reader-only author ids.
READER_SYNTHETIC_AUTHOR_HASH_MARKER = "reader_synth_author"
