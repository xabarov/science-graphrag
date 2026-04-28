#!/usr/bin/env python3
"""CI-friendly entrypoint: same checks as ``build_research_chat_prompt_bundle.py --evaluate``."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    """Run ``build_research_chat_prompt_bundle.py --evaluate``; propagate exit code."""
    script = Path(__file__).resolve().parent / "build_research_chat_prompt_bundle.py"
    return subprocess.call(
        [sys.executable, str(script), "--evaluate"],
        cwd=_ROOT,
    )


if __name__ == "__main__":
    raise SystemExit(main())
