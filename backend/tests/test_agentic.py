from src.providers.router import ProviderRouter
from src.retrieval.agentic import _stub_decompose, agentic_retrieve


def test_stub_decompose_splits_on_conjunction():
    plan = _stub_decompose("Apple revenue and Microsoft revenue")
    assert plan.sub_queries[0] == "Apple revenue and Microsoft revenue"
    assert any("Microsoft revenue" in s for s in plan.sub_queries)


def test_stub_decompose_capped():
    plan = _stub_decompose("a and b and c and d and e")
    assert len(plan.sub_queries) <= 3


def test_agentic_accumulates_across_subqueries(settings, seeded_retriever):
    router = ProviderRouter(settings)  # stub mode -> uses _stub_decompose
    res = agentic_retrieve(
        seeded_retriever,
        router,
        "Apple total net sales and Microsoft total revenue",
        top_k=6,
    )
    assert res.route == "agentic"
    tickers = {c.metadata.ticker for c in res.chunks}
    # Sub-queries pull evidence for both companies.
    assert "AAPL" in tickers and "MSFT" in tickers
    assert res.citations


def test_agentic_records_trace(settings, seeded_retriever):
    router = ProviderRouter(settings)
    trace: list = []
    agentic_retrieve(seeded_retriever, router, "revenue and margins", trace=trace)
    assert trace  # decompose call recorded
