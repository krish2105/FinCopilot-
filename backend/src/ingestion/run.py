"""Ingestion CLI.

python -m src.ingestion.run                        # all configured tickers
python -m src.ingestion.run --tickers AAPL MSFT    # subset
python -m src.ingestion.run --sources market news  # skip EDGAR
python -m src.ingestion.run --offline              # local embeddings, no LLM API
"""

from __future__ import annotations

import argparse
import json
import logging

from src.config.settings import get_settings
from src.ingestion.embed import Embedder
from src.ingestion.pipeline import DEFAULT_SOURCES, ingest
from src.retrieval.store import get_vector_store


def main() -> None:
    parser = argparse.ArgumentParser(description="FinCopilot ingestion pipeline")
    parser.add_argument("--tickers", nargs="*", help="Tickers (default: from config)")
    parser.add_argument(
        "--sources",
        nargs="*",
        default=list(DEFAULT_SOURCES),
        choices=["edgar", "subsidiaries", "market", "news"],
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Force local embeddings (no Gemini API calls)",
    )
    args = parser.parse_args()

    settings = get_settings()
    if args.offline:
        settings.fincopilot_offline_mode = True

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    embedder = Embedder(settings)
    store = get_vector_store(embedder.dim, embedder.name, settings)
    stats = ingest(
        tickers=args.tickers,
        sources=tuple(args.sources),
        settings=settings,
        store=store,
        embedder=embedder,
    )
    print(json.dumps(stats.as_dict(), indent=2))


if __name__ == "__main__":
    main()
