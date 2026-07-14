"""XBRL: exact financial facts, looked up rather than retrieved (Phase 45).

Every 10-K and 10-Q is filed with machine-readable XBRL tags, and the SEC serves all
of it for free, with no API key and no daily cap. That matters enormously here.

Retrieving a *number* from prose is the weakest thing a RAG system does: on a
23k-query financial benchmark, **73% of retrieval failures were table-structure
mismatches** — the figure lives in a cell, and an embedding of the question simply
cannot match it. And FinanceBench found GPT-4-Turbo *with retrieval* got **81% of
financial questions wrong or refused**. The failure is arithmetic and lookup, not
prose comprehension.

So: prose stays in the vector/FTS index, and numbers come from here — exact, typed,
period-aligned, and citable back to the accession number they were filed under. The
model never has to "remember" a figure, and the faithfulness gate gets a ground truth
to check against.
"""
