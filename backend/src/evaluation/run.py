"""RAGAS evaluation CLI.

    python -m src.evaluation.run                 # full benchmark subset
    python -m src.evaluation.run --limit 10      # quick smoke run
    FINCOPILOT_EMBED_BACKEND=local python -m src.evaluation.run   # semantic stack

Writes eval/results/latest.json (+ a timestamped copy). With a GEMINI_API_KEY
configured, canonical RAGAS metrics are added alongside the deterministic ones.
"""

from __future__ import annotations

import argparse
import json
import logging

from src.config.settings import get_settings
from src.evaluation.harness import run_eval


def main() -> None:
    parser = argparse.ArgumentParser(description="FinCopilot RAGAS evaluation")
    parser.add_argument("--limit", type=int, default=None, help="Evaluate first N questions")
    args = parser.parse_args()

    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    result = run_eval(settings, limit=args.limit)
    print(
        json.dumps(
            {"metrics": result["metrics"], "ragas": result["ragas"], "stack": result["stack"]},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
