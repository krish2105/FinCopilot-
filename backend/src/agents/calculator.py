"""Exact-arithmetic tool + guardrail (Phase 26).

LLMs are unreliable at arithmetic — fatal in finance. This module provides:

- ``safe_eval`` — evaluate a numeric expression with a restricted AST (no names,
  calls, or attribute access; only + - * / ** % and parentheses). Never uses
  Python ``eval``.
- finance helpers — ``percent_change``, ``cagr``, ``ratio``.
- ``verify_arithmetic`` — scan an answer for explicit ``A op B = C`` claims and
  recompute them, returning any that are wrong. Wired into the faithfulness gate
  so a miscalculated figure fails the "insufficient evidence" check just like an
  ungrounded number does.
"""

from __future__ import annotations

import ast
import operator
import re

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _ev(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_ev(node.left), _ev(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_ev(node.operand))
    raise ValueError("unsupported expression")


def safe_eval(expr: str) -> float | None:
    """Evaluate a pure-arithmetic expression, or None if invalid/unsafe."""
    try:
        tree = ast.parse(expr.strip(), mode="eval")
        return _ev(tree.body)
    except Exception:  # noqa: BLE001
        return None


def percent_change(old: float, new: float) -> float | None:
    """Percentage change from ``old`` to ``new`` (None if old is 0)."""
    if not old:
        return None
    return (new - old) / abs(old) * 100.0


def cagr(begin: float, end: float, years: float) -> float | None:
    """Compound annual growth rate as a percentage."""
    if begin is None or end is None or begin <= 0 or end <= 0 or years <= 0:
        return None
    return ((end / begin) ** (1.0 / years) - 1.0) * 100.0


def ratio(numerator: float, denominator: float) -> float | None:
    if not denominator:
        return None
    return numerator / denominator


def evaluate(expression: str) -> dict:
    """Structured result for a tool-style call."""
    val = safe_eval(expression)
    return {"expression": expression, "value": val, "ok": val is not None}


# --- arithmetic verifier (faithfulness guardrail) ------------------------------
_EXPR_RE = re.compile(
    r"(-?[\d,]+(?:\.\d+)?)\s*([-+*/])\s*(-?[\d,]+(?:\.\d+)?)\s*=\s*(-?[\d,]+(?:\.\d+)?)"
)


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def verify_arithmetic(text: str, rel_tol: float = 0.02) -> list[dict]:
    """Find explicit ``A op B = C`` claims in ``text`` and return the wrong ones."""
    errors: list[dict] = []
    for m in _EXPR_RE.finditer(text):
        a, op, b, claimed_s = m.groups()
        computed = safe_eval(f"{_num(a)}{op}{_num(b)}")
        if computed is None:
            continue
        claimed = _num(claimed_s)
        denom = max(1.0, abs(claimed))
        if abs(computed - claimed) / denom > rel_tol:
            errors.append(
                {
                    "expression": m.group(0),
                    "claimed": claimed,
                    "correct": round(computed, 4),
                }
            )
    return errors
