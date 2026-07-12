"""Loader for the real benchmark question set (eval/test_questions.jsonl).

Questions are sampled from FinanceBench (real, human-curated open-book QA over
real 10-Ks). Each carries the gold answer and the gold evidence passage from the
filing — no synthetic data. See DATA_SOURCES.md.
"""

from __future__ import annotations

import json
import os

from pydantic import BaseModel


class EvalQuestion(BaseModel):
    id: str
    benchmark: str
    company: str
    ticker: str
    doc_name: str = ""
    question_type: str = ""
    question: str
    answer: str  # gold
    evidence: str  # gold supporting passage from the real filing
    page: int | None = None


def default_dataset_path() -> str:
    # repo_root/eval/test_questions.jsonl (backend/src/evaluation -> up 3)
    here = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(here, "..", "..", "..", "eval", "test_questions.jsonl"))


def load_questions(path: str | None = None) -> list[EvalQuestion]:
    path = path or default_dataset_path()
    out: list[EvalQuestion] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('{"_comment'):
                continue
            data = json.loads(line)
            if "question" not in data:
                continue
            out.append(EvalQuestion(**data))
    return out
