"""Common interface for layer-specific dual-validate extractors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from scripts.dual_validate.consistency_report import ConsistencyReport
from scripts.dual_validate.llm_client import DualValidateLLMClient, LLMCallSpec, prompt_hash
from scripts.dual_validate.matcher import EmbeddingScorerProtocol


@dataclass(frozen=True)
class ExtractorRunOutput:
    """Result of one ``extract_b_for_pack`` run; bundles raw + structured + spec."""

    raw_response: str
    structured_b: list[dict]
    call_spec: LLMCallSpec
    prompt_hash: str
    latency_ms: int
    usage_tokens: dict[str, int]


class ExtractorBase(ABC):
    """Layer-specific extractor — one concrete subclass per Corpus Gold Pack v1 layer."""

    layer_name: str = "abstract"

    @abstractmethod
    def discover_packs(self, fixtures_root: Path) -> list[Path]:
        """Return all candidate pack directories for this layer under ``fixtures_root``."""

    @abstractmethod
    def build_call_spec(self, pack_dir: Path, *, model: str, base_url: str) -> LLMCallSpec:
        """Construct the LLM prompt for one pack (system + user prompts)."""

    @abstractmethod
    def parse_response(self, raw_response: str) -> list[dict]:
        """Parse the LLM response into a list of records B."""

    @abstractmethod
    def build_report(
        self,
        pack_dir: Path,
        *,
        run: ExtractorRunOutput | None,
        gold_a: dict,
        embedding_scorer: EmbeddingScorerProtocol | None = None,
    ) -> ConsistencyReport:
        """Compute matcher diff and produce the consistency report (no I/O).

        ``embedding_scorer``, when provided, enables the embedding cascade in the
        matcher (see ``match_records``). Implementations should forward it.
        """

    def run_for_pack(
        self,
        pack_dir: Path,
        *,
        client: DualValidateLLMClient | None,
        model: str,
        base_url: str,
        dry_run: bool,
    ) -> tuple[ExtractorRunOutput | None, LLMCallSpec]:
        """Build the prompt, optionally invoke the LLM, return raw + parsed payload."""

        spec = self.build_call_spec(pack_dir, model=model, base_url=base_url)
        if dry_run or client is None:
            return None, spec
        result = client.call(spec)
        structured = self.parse_response(result.content)
        run = ExtractorRunOutput(
            raw_response=result.content,
            structured_b=structured,
            call_spec=spec,
            prompt_hash=result.prompt_hash,
            latency_ms=result.latency_ms,
            usage_tokens=result.usage_tokens,
        )
        return run, spec

    def rebuild_run_from_raw(
        self,
        pack_dir: Path,
        *,
        raw_path: Path,
        prior_report: dict | None,
    ) -> ExtractorRunOutput:
        """Reconstruct an ExtractorRunOutput from a saved raw response (no LLM call).

        Used for matcher-only re-runs: tweak the matcher, refresh consistency reports
        without spending tokens. Provenance fields are pulled from the prior report
        when available, otherwise filled with neutral defaults.
        """

        raw_text = raw_path.read_text()
        structured = self.parse_response(raw_text)
        prior_b = (prior_report or {}).get("extractor_b", {}) if prior_report else {}
        spec = self.build_call_spec(
            pack_dir,
            model=str(prior_b.get("model", "rebuild_from_raw")),
            base_url=str(prior_b.get("base_url", "rebuild_from_raw")),
        )
        return ExtractorRunOutput(
            raw_response=raw_text,
            structured_b=structured,
            call_spec=spec,
            prompt_hash=str(prior_b.get("prompt_hash", prompt_hash(spec))),
            latency_ms=int(prior_b.get("latency_ms", 0)),
            usage_tokens=dict(prior_b.get("usage_tokens", {"total": 0})),
        )
