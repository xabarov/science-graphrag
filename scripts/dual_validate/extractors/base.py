"""Common interface for layer-specific dual-validate extractors."""

from __future__ import annotations

import dataclasses
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.dual_validate.consistency_report import ConsistencyReport
from scripts.dual_validate.llm_client import DualValidateLLMClient, LLMCallSpec, prompt_hash
from scripts.dual_validate.matcher import EmbeddingScorerProtocol

_FENCED = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def parse_json_object_lenient(raw: str) -> Any:
    """Parse a JSON object out of a possibly-noisy LLM response.

    LLMs occasionally append commentary, repeat the object twice, or wrap the
    body in ``` fences even when ``response_format=json_object`` was requested.
    We try, in order:

    1. straight ``json.loads`` of the trimmed payload;
    2. unwrap a ``` ... ``` fence if present and retry;
    3. ``json.JSONDecoder().raw_decode`` to consume only the leading object.

    Raises ``ValueError`` if none of these succeed; the caller wraps the message
    with extractor-specific context.
    """

    text = raw.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fenced = _FENCED.search(text)
    if fenced is not None:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass

    decoder = json.JSONDecoder()
    start = text.find("{")
    if start >= 0:
        try:
            obj, _ = decoder.raw_decode(text[start:])
            return obj
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"could not decode JSON from LLM response: {exc.msg} " f"at offset {exc.pos}"
            ) from exc

    raise ValueError("LLM response contained no JSON object")


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
        max_output_tokens_override: int | None = None,
        reasoning_override: dict[str, Any] | None = None,
    ) -> tuple[ExtractorRunOutput | None, LLMCallSpec]:
        """Build the prompt, optionally invoke the LLM, return raw + parsed payload.

        ``max_output_tokens_override`` raises the per-extractor ``max_tokens`` ceiling.
        Required for reasoning-style models (e.g. ``moonshotai/kimi-k2.6``) that spend
        a large slice of the budget on hidden chain-of-thought before emitting JSON.

        ``reasoning_override`` forwards an OpenRouter ``reasoning`` payload (e.g.
        ``{"enabled": False}`` to suppress hidden CoT). When ``None`` we leave the
        spec's default reasoning policy alone.
        """

        spec = self.build_call_spec(pack_dir, model=model, base_url=base_url)
        if max_output_tokens_override is not None and max_output_tokens_override > spec.max_tokens:
            spec = dataclasses.replace(spec, max_tokens=max_output_tokens_override)
        if reasoning_override is not None:
            spec = dataclasses.replace(spec, reasoning=dict(reasoning_override))
        if dry_run or client is None:
            return None, spec
        result = client.call(spec)
        try:
            structured = self.parse_response(result.content)
        except Exception as exc:
            # Surface the raw body so the CLI can save it for offline inspection
            # (e.g. when a model returns prose-only or an unsupported JSON shape).
            setattr(exc, "raw_response", result.content)
            raise
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
