"""Runs the full agent pipeline over the benchmark questions and scores it.

Each question flows through the real Orchestrator → Researcher → Analyst →
Compliance → synthesize → Self-RAG gate, over the eval corpus. We then compute
deterministic metrics (always) and RAGAS (when an LLM key is configured), and
write the results to eval/results/ for the API + dashboard to serve.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime

from src.agents.orchestrator import AgentGraph
from src.config.settings import Settings, get_settings
from src.evaluation import metrics as M
from src.evaluation.corpus import build_eval_retriever
from src.evaluation.dataset import default_dataset_path, load_questions
from src.providers.router import ProviderRouter

logger = logging.getLogger(__name__)


def results_dir() -> str:
    """Where eval results are written — and, crucially, where the API can read them.

    These used to live at the repo root (`<repo>/eval/results`). But render.yaml sets
    `rootDir: backend`, so the Docker build context is `backend/` only: the repo-root
    directory is simply not in the image. `GET /eval` was therefore reading a path that
    could never exist in production, and the Evaluation dashboard showed "No run yet"
    forever — no matter how many evals we ran or committed.

    Results now live *inside* the backend package so they ship with the image.
    """
    here = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(here, "..", "..", "eval_results"))


def latest_results_path() -> str:
    return os.path.join(results_dir(), "latest.json")


def _source_qid(url: str) -> str:
    return url.rsplit("/", 1)[-1] if url else ""


def run_eval(
    settings: Settings | None = None,
    limit: int | None = None,
    dataset_path: str | None = None,
    write: bool = True,
) -> dict:
    settings = settings or get_settings()
    questions = load_questions(dataset_path or default_dataset_path())
    if limit:
        questions = questions[:limit]

    retriever = build_eval_retriever(questions, settings)
    router = ProviderRouter(settings)
    graph = AgentGraph(retriever=retriever, router=router, entity_graph=None, settings=settings)

    per_question: list[dict] = []
    ragas_records: list[dict] = []

    for q in questions:
        ans = graph.run(q.question, tickers=[q.ticker])
        source_qids = {_source_qid(c.source_url) for c in ans.citations}
        context_hit = q.id in source_qids
        contexts = [c.excerpt for c in ans.citations if c.excerpt]
        answer_match = M.answer_matches(q.answer, ans.answer) or M.answer_matches(
            q.answer, " ".join(contexts)
        )
        faithful = ans.faithfulness.faithful and ans.verdict == "ok"

        per_question.append(
            {
                "id": q.id,
                "company": q.company,
                "question": q.question[:160],
                "gold": q.answer[:80],
                "generated": ans.answer[:200],
                "route": ans.route,
                "verdict": ans.verdict,
                "context_hit": int(context_hit),
                "answer_match": int(answer_match),
                "faithful": int(faithful),
                "has_citation": int(len(ans.citations) > 0),
                "refused": int(ans.verdict != "ok"),
                "latency_ms": ans.latency_ms,
            }
        )
        ragas_records.append(
            {
                "question": q.question,
                "answer": ans.answer,
                "contexts": contexts or [q.evidence[:1000]],
                "ground_truth": q.answer,
            }
        )

    agg = M.aggregate(per_question)
    ragas = M.compute_ragas(ragas_records)

    result = {
        "benchmark": "FinanceBench",
        "generated_at": datetime.now(UTC).isoformat(),
        "n_questions": len(questions),
        "n_companies": len({q.company for q in questions}),
        "stack": {
            "embed_backend": f"{retriever.embedder.backend}:{retriever.embedder.name}",
            "reranker": retriever.reranker.name,
            "llm_mode": router.mode,
        },
        "metrics": agg,
        "ragas": ragas,
        "per_question": per_question,
    }

    if write:
        os.makedirs(results_dir(), exist_ok=True)
        with open(latest_results_path(), "w") as f:
            json.dump(result, f, indent=2)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        with open(os.path.join(results_dir(), f"ragas_{stamp}.json"), "w") as f:
            json.dump(result, f, indent=2)

    logger.info("eval done | %s", agg)
    return result
