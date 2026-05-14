"""LLM prompt templates for ``retrieval_v1`` dual-validate extractors."""

from __future__ import annotations

WORKSPACE_SCOPED_SYSTEM = (
    "You are an independent retrieval reviewer. Given a question, the papers "
    "available in a workspace, and the rest of the corpus that is OUT OF "
    "scope, decide which workspace papers should be cited and flag any "
    "out-of-scope papers you would have mistakenly added. Always answer as a "
    "JSON object."
)

WORKSPACE_SCOPED_USER = """Workspace: {ws_name}
Workspace papers (in scope):
{workspace_block}

Out-of-scope papers (must NOT be cited):
{forbidden_block}

QUESTION:
{question}

Output STRICTLY this JSON object — no prose, no markdown:
{{
  "expected_corpus_work_ids": ["<id from workspace>", ...],
  "would_violate_workspace_with": ["<id from out-of-scope>", ...],
  "rationale": "<one sentence>"
}}
"""

HYBRID_ABLATION_SYSTEM = (
    "You are an independent retrieval reviewer. Given a question and a list "
    "of candidate papers, classify each candidate as relevant or irrelevant "
    "to the question. Always answer as a JSON object."
)

HYBRID_ABLATION_USER = """QUESTION:
{question}

Candidate papers:
{candidates_block}

Output STRICTLY this JSON object — no prose, no markdown:
{{
  "relevant_corpus_work_ids": ["<id>", ...],
  "irrelevant_corpus_work_ids": ["<id>", ...],
  "rationale": "<one sentence>"
}}
"""

MULTIHOP_SYSTEM = (
    "You are an independent multihop-retrieval reviewer. Given a question, "
    "an indication of whether the answer is an ordered chain of papers or an "
    "unordered set of papers / authors, and an inventory of candidate papers, "
    "produce the expected ids (and order, if a chain). Always answer as a "
    "JSON object."
)

MULTIHOP_USER_CHAIN = """QUESTION:
{question}

Expected path kind: ordered_chain (later items extend / cite earlier items)

Candidate inventory:
{candidates_block}

Output STRICTLY this JSON object — no prose, no markdown:
{{
  "expected_chain_corpus_work_ids": ["<id>", "<id>", ...],
  "rationale": "<one sentence>"
}}
"""

MULTIHOP_USER_SET = """QUESTION:
{question}

Expected path kind: unordered_set ({node_kind})

Candidate paper inventory (use to ground your answer):
{candidates_block}

Output STRICTLY this JSON object — no prose, no markdown:
{{
  "expected_node_canonical_names": ["<name>", "<name>", ...],
  "rationale": "<one sentence>"
}}
"""

__all__ = [
    "HYBRID_ABLATION_SYSTEM",
    "HYBRID_ABLATION_USER",
    "MULTIHOP_SYSTEM",
    "MULTIHOP_USER_CHAIN",
    "MULTIHOP_USER_SET",
    "WORKSPACE_SCOPED_SYSTEM",
    "WORKSPACE_SCOPED_USER",
]
